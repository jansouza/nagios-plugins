#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_tomcat.py
# Version : 0.2
# Date    : Sep 02, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_tomcat.py -H 127.0.0.1 -p 8080 -a basic_auth -M 80 90 -C 80 90
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_tomcat
#    command_line    $USER1$/check_tomcat.py -H $HOSTADDRESS$ -a $ARG1$ -T $ARG2$ -M $ARG3$ -C $ARG4$ $ARG5$
# }
#
# Arguments and thresholds are:
#  ARG1 : Basic Authentication (use basic_encode.py)
#  ARG2 : Response Time Threshold. Below it is >0.3s for WARNING, >0.5s for critical
#  ARG3 : Memory Heap  Threshold. Below it is >80% for WARNING, >90% for critical
#  ARG4 : Threads Busy Threshold. Below it is >80% for warning, >90% for critical
#  ARG5 : Others arguments. Below set connections TimeOut
#
# define service {
#       use                     prod-service
#       service_description     TOMCAT STATUS
#       check_command           check_tomcat!dG9tY2F0OnRvbWNhdA==!0.3 0.5!80 90!80 90!-t 10
#       hostgroups              tomcat
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Sep 2019] First version of the code.
#  [0.2 - Sep 2019] Fix request timeout
#
#
#  TODO
#     (a) Get Server Information
#     (b) Get Connectors Request Info (bytes_received, bytes_sent)
#     (C) Get Memory Pool Informations
#
# ============================ START OF PROGRAM CODE =============================
# sudo pip install requests | sudo easy_install requests
# https://pypi.org/project/requests/

import argparse
import logging
import os, sys, time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import xml.etree.ElementTree as ET
from math import log

# NAGIOS return codes :
# https://nagios-plugins.org/doc/guidelines.html#AEN78
OK       = 0
WARNING  = 1
CRITICAL = 2
UNKNOWN  = 3

mylogger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)

def debug_factory(logger, debug_level):
   """
   Decorate logger in order to add custom levels for Nagios
   """
   def custom_debug(msg, *args, **kwargs):
       if logger.level >= debug_level:
           return
       logger._log(debug_level, msg, args, kwargs)
   return custom_debug

def get_args():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description="TOMCAT Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 8080)', dest='port', type=str, default=['8080'])
   parser.add_argument('-U', nargs=1, required=False, help='Status URL Context', dest='context', type=str, default=['/manager'])

   parser.add_argument('-a', nargs=1, required=True, help='Authentication (use basic_encoder.py)', dest='basic_auth', type=str)

   parser.add_argument('-T', nargs=2, required=False, help='Measure the output connection response time in seconds -T [WARN,CRIT] \n Ex.: -T 0.1 0.5', dest='response_time', type=str)
   parser.add_argument('-M', nargs=2, required=False, help='Measure the percent of used memory heap -M [WARN,CRIT] \n Ex.: -C 80 90', dest='mem_used', type=str)
   parser.add_argument('-C', nargs=2, required=False, help='Measure the percent of Threads Busy -C [WARN,CRIT] \n Ex.: -C 80 90', dest='threads_busy', type=str)

   parser.add_argument('-t', nargs=1, required=False, help='Connection TimeOut', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args

# convert human readable size function
def sizeof_fmt(num):
    # Human friendly size
    unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2])
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{0:.%sf} {1}' % (num_decimals)
        return format_string.format(quotient, unit)
    elif num == 0:
        return '0 bytes'
    elif num == 1:
        return '1 byte'
    elif num < 0:
        return 'negative number'
    else:
        return None

def main():
   # Handling arguments
   args = get_args()

   host = args.host[0]
   port = args.port[0]

   #Authentication
   basic_auth = args.basic_auth[0]

   if args.response_time:
       response_warn   = args.response_time[0]
       response_crit   = args.response_time[1]

   if args.mem_used:
       mem_used_warn   = args.mem_used[0]
       mem_used_crit   = args.mem_used[1]

   if args.threads_busy:
       threads_busy_warn   = args.threads_busy[0]
       threads_busy_crit   = args.threads_busy[1]

   #URL Context
   context = args.context[0]

   timeout = 10
   if args.timeout:
     timeout = args.timeout[0]

   verbose = args.verbose
   # Logging settings
   if verbose:
       log_level = logging.DEBUG
   else:
       log_level = logging.INFO

   # Add custom level unknown
   logging.addLevelName(logging.DEBUG+1, 'UNKOWN')
   setattr(mylogger, 'unkown', debug_factory(mylogger, logging.DEBUG+1))

   # Change INFO LevelName to OK
   logging.addLevelName(logging.INFO, 'OK')

   # Setting output format for Nagios
   logging.basicConfig(stream=sys.stdout,format='%(levelname)s - %(message)s',level=log_level)

   ############
   #GET DATA
   ###########

   resp_time=0
   status = {}
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s CONTEXT: %s TIMEOUT: %s" % (host,port,context,timeout))
     start = time.time()

     url = "http://" + host + ":" + port + context + "/status/all?XML=true"
     mylogger.debug("URL: %s" % (url))

     headers = {'Authorization': 'Basic %s' % basic_auth}
     mylogger.debug(headers)
     res = requests.get(url, verify=False, headers=headers, timeout=timeout)

     if res.status_code != 200:
        mylogger.critical(str(res.status_code) + " Found")
        sys.exit(CRITICAL)

     html = res.text
     end = time.time()
     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (html is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   try:
       tree_xml = ET.fromstring(html)
   except ET.ParseError as e:
       tree_xml="ERROR: I Can't understand the XML page. Error: %s" %(e)
       sys.exit(CRITICAL)

   #show XML tree
   #mylogger.debug(ET.dump(tree_xml))

   status_memory = {}
   memory = tree_xml.find('.//memory')

   free_memory  = float(memory.get('free'))
   total_memory = float(memory.get('total'))
   max_memory = float(memory.get('max'))
   available_memory = free_memory + max_memory - total_memory
   used_memory = max_memory - available_memory

   status_memory['free_memory'] = free_memory
   status_memory['total_memory'] = total_memory
   status_memory['max_memory'] = max_memory
   status_memory['available_memory'] = available_memory
   status_memory['used_memory'] = used_memory
   status_memory['percent_used_memory'] = round(float((used_memory * 100)/max_memory),2)

   mylogger.debug(status_memory)

   status_conn = {}
   for connector in tree_xml.findall('./connector'):
        connector_name = str(connector.get('name'))
        thread = connector.find('./threadInfo')

        max_thread = float(thread.get('maxThreads'))
        busy_thread = float(thread.get('currentThreadsBusy'))
        percent_thread = round(float((busy_thread * 100)/max_thread),2)

        status_conn[connector_name] = [{'max_thread': max_thread}, {'busy_thread': busy_thread}, {'percent_thread': percent_thread}]

   mylogger.debug(status_conn)

   ############
   #perfdata
   ###########

   #response_time
   resp_warn_data = ""
   resp_crit_data = ""
   if args.response_time:
      resp_warn_data = round(float(response_warn), 6)
      resp_crit_data = round(float(response_crit), 6)
   resp_time_data = str(resp_time) + ";" + str(resp_warn_data) + ";" + str(resp_crit_data) + ";0.000000"

   #Memory Heap
   mem_warn_data = ""
   mem_crit_data = ""
   if args.mem_used:
      mem_warn_data = mem_used_warn
      mem_crit_data = mem_used_crit

   percent_used_memory = status_memory['percent_used_memory']
   used_memory = str(status_memory['used_memory'])
   max_memory = str(status_memory['max_memory'])

   mem_used_data = str(percent_used_memory) + ";" + str(mem_warn_data) + ";" + str(mem_crit_data) + ";0"
   heap_size_data = str(used_memory) + ";" + "0" + ";" + str(max_memory) + ";0"

   #Threads Busy
   threads_warn_data = ""
   threads_crit_data = ""
   if args.threads_busy:
      threads_warn_data = threads_busy_warn
      threads_crit_data = threads_busy_crit

   threads_data = ""
   threads2_data = ""
   for connector in status_conn :
       values = status_conn[connector]
       max_thread = values[0].get('max_thread')
       busy_thread = values[1].get('busy_thread')
       percent_thread = values[2].get('percent_thread')

       connector_name = str(connector).replace("\"","")

       threads_data += connector_name + "_percent_thread=" +  str(percent_thread) + ";" + str(threads_warn_data) + ";" + str(threads_crit_data) + ";0 "
       threads2_data += connector_name + "_busy_thread=" +  str(busy_thread) + ";0;" + str(max_thread) + ";0 "

   perfdata = "response_time=%s mem_used=%s heap_size=%s %s%s" % (resp_time_data,mem_used_data,heap_size_data,threads_data,threads2_data)

   output = str(res.request.url) + " - " + str(res.status_code) + " | " + perfdata

   ############
   #Threshold
   ###########

   #Response Time
   if args.response_time:
	   mylogger.debug("Response Time WARN: %s, CRIT %s " % (response_warn,response_crit) )

	   resp_warn = round(float(response_warn), 6)
	   resp_crit = round(float(response_crit), 6)

	   if (resp_time >= resp_crit) :
            mylogger.critical("response_time %s > %s" % (resp_time,resp_crit) + " - " + output )
            sys.exit(CRITICAL)
	   elif (resp_time >= resp_warn) :
	        mylogger.warning("response_time %s > %s" % (resp_time,resp_warn) + " - " + output )
	        sys.exit(WARNING)

   #Memory Heap
   if args.mem_used:
	   mylogger.debug("Memory Used WARN: %s, CRIT %s " % (mem_used_warn,mem_used_crit) )

	   if (percent_used_memory >= float(mem_used_crit)) :
	       mylogger.critical("Memory Used %s > %s" % (percent_used_memory,mem_used_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (percent_used_memory >= float(mem_used_warn)) :
	       mylogger.warning("Memory Used %s > %s" % (percent_used_memory,mem_used_warn) + " - " + output )
	       sys.exit(WARNING)

   #Threads Busy
   if args.threads_busy:
       mylogger.debug("Treads Busy WARN: %s, CRIT %s " % (threads_busy_warn,threads_busy_crit) )

       for connector in status_conn:
            values = status_conn[connector]
            max_thread = values[0].get('max_thread')
            busy_thread = values[1].get('busy_thread')
            percent_thread = values[2].get('percent_thread')

            if (percent_thread >= float(threads_busy_crit)) :
                mylogger.critical("Treads Busy %s > %s" % (percent_thread,threads_busy_crit) + " - " + output )
                sys.exit(CRITICAL)
            elif (percent_thread >= float(threads_busy_warn)) :
                mylogger.warning("Treads Busy %s > %s" % (percent_thread,threads_busy_warn) + " - " + output )
                sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
