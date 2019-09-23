#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_jboss.py
# Version : 0.1
# Date    : Sep 15, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_jboss.py -H 127.0.0.1 -P 9990 -u jboss -p jboss -M 80 90
#
# Tested on : JBOSS AS 7.1 WILDFLY 10.1 WILDFLY 17.1 JBOSS EAP 7
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_jboss
#    command_line    $USER1$/check_jboss.py -H $HOSTADDRESS$ -u $ARG1$ -p $ARG2$ -M $ARG3$
# }
#
# Arguments and thresholds are:
#  ARG1 : JBoss management console username
#  ARG2 : JBoss management console Password
#  ARG3 : Memory Heap  Threshold. Below it is >80% for WARNING, >90% for critical
#  ARG5 : Others arguments. Below set connections Timeout
#
# define service {
#       use                     prod-service
#       service_description     WILDFLY STATUS
#       check_command           check_jboss!jboss!jboss!80 90!-t 10
#       hostgroups              wildfly
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Sep 2019] First version of the code.
#
#  TODO
#     (a) Get Threads Informations
#     (b) Get Server Information
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
   parser = argparse.ArgumentParser(description="WILDFLY Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-P', nargs=1, required=False, help='port number (default: 9990)', dest='port', type=str, default=['9990'])
   parser.add_argument('-U', nargs=1, required=False, help='Status URL Context', dest='context', type=str, default=['/management'])

   parser.add_argument('-u', nargs=1, required=True, help='username', dest='username', type=str)
   parser.add_argument('-p', nargs=1, required=True, help='password', dest='password', type=str)

   parser.add_argument('-M', nargs=2, required=False, help='Measure the percent of used memory heap -M [WARN,CRIT] \n Ex.: -C 80 90', dest='mem_used', type=str)

   parser.add_argument('-t', nargs=1, required=False, help='Connection TimeOut', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args

def main():
   # Handling arguments
   args = get_args()

   host = args.host[0]
   port = args.port[0]

   #Authentication
   username = args.username[0]
   password = args.password[0]

   if args.mem_used:
       mem_used_warn   = args.mem_used[0]
       mem_used_crit   = args.mem_used[1]

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

     url = "http://" + host + ":" + port + context + "/core-service/platform-mbean/type/memory?operation=attribute&name=heap-memory-usage"
     mylogger.debug("URL: %s" % (url))

     headers = {'content-type': 'application/json'}
     auth=requests.auth.HTTPDigestAuth(username,password)
     mylogger.debug(headers)

     res = requests.get(url,headers=headers,auth=auth, timeout=timeout)

     if res.status_code != 200:
        mylogger.critical(str(res.status_code) + " Found")
        sys.exit(CRITICAL)

     status_mem = res.json()
     end = time.time()
     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (status_mem is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   mylogger.debug(status_mem)

   ############
   #perfdata
   ###########

   #Memory Heap
   mem_warn_data = ""
   mem_crit_data = ""
   if args.mem_used:
       mem_warn_data = mem_used_warn
       mem_crit_data = mem_used_crit

   used_heap = int(status_mem['used'])
   max_heap = int(status_mem['max'])
   percent_used_memory = round((float(used_heap * 100) / max_heap), 2)

   mem_used_data = str(percent_used_memory) + "%;" + str(mem_warn_data) + ";" + str(mem_crit_data)
   heap_size_data = str(used_heap) + ";;;" + str(max_heap)

   perfdata = "heap_percent_used=%s heap_size=%s" % (mem_used_data,heap_size_data)

   output = str(host + ":" + port + context) + " | " + perfdata

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
