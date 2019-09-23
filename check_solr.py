#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_solr.py
# Version : 0.2
# Date    : Sep 17, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_solr.py -H 127.0.0.1 -p 8983 -M 80 90
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_solr
#    command_line    $USER1$/check_solr.py -H $HOSTADDRESS$ -M $ARG1$  $ARG2$
# }
#
# Arguments and thresholds are:
#  ARG1 : Memory Heap  Threshold. Below it is >80% for WARNING, >90% for critical
#  ARG2 : Others arguments. Below set connections Timeout
#
# define service {
#       use                     prod-service
#       service_description     SOLR STATUS
#       check_command           check_solr!80 90!-t 10
#       hostgroups              solr
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Sep 2019] First version of the code.
#  [0.2 - Sep 2019] Fix Authentication argument
#
#
#  TODO
#     (a) Get Threads Information
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

def convert_to_days(milliseconds):
    """Return the tuple of days, hours, minutes and seconds."""

    seconds = milliseconds / 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return "%s days, %s hours, %s minutes" % (days, hours, minutes)

def get_args():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description="Apache Solr Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 8983)', dest='port', type=str, default=['8983'])

   parser.add_argument('-a', nargs=1, required=False, help='Authentication (use basic_encoder.py)', dest='basic_auth', type=str)
   parser.add_argument('-M', nargs=2, required=False, help='Measure the percent of used memory heap -M [WARN,CRIT] \n Ex.: -C 80 90', dest='mem_used', type=str)

   parser.add_argument('-t', nargs=1, required=False, help='Connection Timeout', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args

def main():
   # Handling arguments
   args = get_args()

   host = args.host[0]
   port = args.port[0]

   #Authentication
   if args.basic_auth:
     basic_auth = args.basic_auth[0]

   if args.mem_used:
       mem_used_warn   = args.mem_used[0]
       mem_used_crit   = args.mem_used[1]

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
   stats = None
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s TIMEOUT: %s" % (host,port,timeout))
     start = time.time()

     url = "http://" + host + ":" + port + "/solr/admin/info/system"
     mylogger.debug("URL: %s" % (url))

     headers = None
     if args.basic_auth:
         headers = {'Authorization': 'Basic %s' % basic_auth}
         mylogger.debug(headers)

     res = requests.get(url, verify=False, headers=headers, timeout=timeout)

     if res.status_code != 200:
        mylogger.critical(str(res.status_code) + " Found")
        sys.exit(CRITICAL)

     stats = res.json()
     end = time.time()
     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (stats is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   #mylogger.debug(stats)

   solr_version = stats.get('lucene').get('solr-spec-version')
   uptime = stats.get('jvm').get('jmx').get('upTimeMS')
   uptime_days = convert_to_days(int(uptime))

   solr_info="solr %s on %s:%s, up %s" % (solr_version,host,port,uptime_days)

   ############
   #perfdata
   ###########

   #Memory Heap
   mem_warn_data = ""
   mem_crit_data = ""
   if args.mem_used:
      mem_warn_data = mem_used_warn
      mem_crit_data = mem_used_crit

   memory_stats = stats.get('jvm').get('memory')
   mylogger.debug(memory_stats)

   percent_used_memory = round(memory_stats.get('raw').get('used%'),2)
   used_memory = memory_stats.get('raw').get('used')
   max_memory = memory_stats.get('raw').get('max')

   mem_used_data = str(percent_used_memory) + "%;" + str(mem_warn_data) + ";" + str(mem_crit_data)
   heap_size_data = str(used_memory) + ";;;" + str(max_memory)

   perfdata = "heap_percent_used=%s heap_used=%s" % (mem_used_data,heap_size_data)

   output = solr_info + " | " + perfdata

   ############
   #Threshold
   ###########
   #Memory Heap
   if args.mem_used:
	   mylogger.debug("Memory Used WARN: %s, CRIT %s " % (mem_used_warn,mem_used_crit) )

	   if (percent_used_memory >= float(mem_used_crit)) :
	       mylogger.critical("Memory Used %s > %s" % (percent_used_memory,mem_used_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (percent_used_memory >= float(mem_used_warn)) :
	       mylogger.warning("Memory Used %s > %s" % (percent_used_memory,mem_used_warn) + " - " + output )
	       sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
