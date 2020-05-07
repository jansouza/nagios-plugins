#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_tomcat_dbcp.py
# Version : 0.3
# Date    : Sep 11, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_tomcat_dbcp.py -H 127.0.0.1 -p 8080 -a basic_auth -j JNDI_NAME
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_tomcat_dbcp
#    command_line    $USER1$/check_tomcat_dbcp.py -H $HOSTADDRESS$ -a $ARG1$ -j $ARG2$ -P $ARG3$ $ARG4$
# }
#
# Arguments and thresholds are:
#  ARG1 : Basic Authentication (use basic_encode.py)
#  ARG2 : JNDI Name
#  ARG3 : Database Pool Utilization Threshold. Below it is >80% for WARNING, >90% for critical
#  ARG4 : Others arguments. Below set connections TimeOut
#
# define service {
#       use                     prod-service
#       service_description     TOMCAT DBCP
#       check_command           check_tomcat_dbcp!dG9tY2F0OnRvbWNhdA==!jdbc/mysql-test!80 90!-t 10
#       hostgroups              tomcat
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Sep 2019] First version of the code.
#  [0.2 - Sep 2019] Ajust perfdata output
#  [0.3 - May 2020] Fix Request lib Log Level
#
#  TODO
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
   parser = argparse.ArgumentParser(description="TOMCAT DBCP Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 8080)', dest='port', type=str, default=['8080'])
   parser.add_argument('-u', nargs=1, required=False, help='Status URL Context', dest='context', type=str, default=['/manager'])

   parser.add_argument('-a', nargs=1, required=True, help='Authentication (use basic_encoder.py)', dest='basic_auth', type=str)
   parser.add_argument('-j', nargs=1, required=True, help='JNDI name', dest='jndi_name', type=str)

   parser.add_argument('-U', nargs=2, required=False, help='Measure the percent of used connections -U [WARN,CRIT] \n Ex.: -U 80 90', dest='pool_used', type=str)

   parser.add_argument('-t', nargs=1, required=False, help='Connection Timeout', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args

def parserJMX(html):
    status_pool = {}
    parsed = {
              'maxIdle':None,
              'minIdle': None,
              'evictionPolicyClassName': None,
              'numActive': None,
              'numIdle': None,
              'jmxName': None,
              'initialSize': None,
              'url': None,
              'maxTotal': None}

    key_count = 0
    context_name = ""
    for line in html.splitlines():
       items = line.split(': ')

       if (items and len(items) != 2):
           continue

       key = items[0]
       value = items[1]

       if key == 'Name' :
           if(key_count > 0):
             status_pool[context_name] = parsed
             key_count = 0
             parsed = {}

           context_name = str(value)
           context_name = context_name.split('context=')[1]
           context_name = context_name.split(',')[0]

       if key == 'maxIdle':
           parsed['maxIdle'] = int(value)
           key_count += 1
       if key == 'minIdle':
            parsed['minIdle'] = int(value)
            key_count += 1
       if key == 'evictionPolicyClassName':
            parsed['evictionPolicyClassName'] = str(value)
            key_count += 1
       if key == 'numActive':
            parsed['numActive'] = int(value)
            key_count += 1
       if key == 'jmxName':
            parsed['jmxName'] = str(value)
            key_count += 1
       if key == 'initialSize':
            parsed['initialSize'] = int(value)
            key_count += 1
       if key == 'url':
            parsed['url'] = str(value)
            key_count += 1
       if key == 'maxTotal' or key == 'maxActive':
            parsed['maxTotal'] = int(value)
            key_count += 1

    status_pool[context_name] = parsed
    if (key_count < 3):
       return None
    else:
       return status_pool

def main():
   # Handling arguments
   args = get_args()

   host = args.host[0]
   port = args.port[0]

   #Authentication
   basic_auth = args.basic_auth[0]
   jndi_name = args.jndi_name[0]

   if args.pool_used:
       pool_used_warn   = args.pool_used[0]
       pool_used_crit   = args.pool_used[1]

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

   #Request Debug Level
   logging.getLogger("urllib3").setLevel(logging.WARNING)
   if verbose:
       logging.getLogger("urllib3").setLevel(logging.DEBUG)

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
   resp_time=0
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s CONTEXT: %s TIMEOUT: %s" % (host,port,context,timeout))
     start = time.time()

     #jmx = "/jmxproxy/?get=Catalina:type=DataSource,path=/bkoffice,host=localhost,class=javax.sql.DataSource,name=jdbc/bkoffice&att=numActive"
     #jmx = "/jmxproxy/?get=Catalina:type=DataSource,host=localhost,context=/BKLaborAPI,class=javax.sql.DataSource,name=\"jdbc/bkoffice\"&att=numActive"
     jmx = "/jmxproxy/?qry=Catalina:type=DataSource,host=localhost,context=*,class=javax.sql.DataSource,name=\"" + jndi_name + "\""

     url = "http://" + host + ":" + port + context + jmx
     mylogger.debug("URL: %s" % (url))

     headers = {'Authorization': 'Basic %s' % basic_auth}
     mylogger.debug(headers)

     res = requests.get(url, verify=False, headers=headers, timeout=timeout)
     if res.status_code != 200:
        mylogger.critical(str(res.status_code) + " Found")
        sys.exit(CRITICAL)

     html = res.text
     mylogger.debug(html)

     stats = parserJMX(html)
     mylogger.debug(stats)

     end = time.time()
     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (stats is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   ############
   #perfdata
   ###########

   #pool_used
   pool_used_warn_data = ""
   pool_used_crit_data = ""
   if args.pool_used:
      pool_used_warn_data = str(round(float(pool_used_warn), 2))
      pool_used_crit_data = str(round(float(pool_used_crit), 2))

   pool_used_perfdata = ""
   dbcp_perfdata = ""
   for context_name in stats :
       values = stats[context_name]
       mylogger.debug(context_name)
       mylogger.debug(values)

       numActive  = values['numActive']
       maxTotal  = values['maxTotal']
       pool_used = numActive * 100 / maxTotal
       pool_used_value = str(round(float(pool_used), 2))

       app_name = str(context_name).replace("/","")
       pool_name = "dbcp_" + app_name

       pool_used_perfdata += "percent_used-" + pool_name + "=" + pool_used_value + "%;"+ pool_used_warn_data +";"+pool_used_crit_data + " "
       dbcp_perfdata += "used-" + pool_name + "=" + str(numActive) + ";;;" + str(maxTotal) + " "

   perfdata = "%s%s" % (pool_used_perfdata,dbcp_perfdata)
   output = str(host + ":" + port + context) + " | " + perfdata

   ############
   #Threshold
   ###########

   #pool_used
   if args.pool_used:
       mylogger.debug("Pool Used WARN: %s, CRIT %s " % (pool_used_warn,pool_used_crit) )

       pool_used_warn = round(float(pool_used_warn), 2)
       pool_used_crit = round(float(pool_used_crit), 2)

       for context_name in stats:
           values = stats[context_name]

           numActive  = values['numActive']
           maxTotal  = values['maxTotal']
           pool_used = round(float(numActive * 100 / maxTotal), 2)
           app_name = str(context_name).replace("/","")
           pool_name = "dbcp_" + app_name

           if (pool_used >= pool_used_crit):
               mylogger.critical("pool_used: %s - %s > %s" % (pool_name,str(pool_used),pool_used_crit) + " - " + output )
               sys.exit(CRITICAL)
           elif (pool_used >= pool_used_warn):
               mylogger.warning("pool_used: %s - %s > %s" % (pool_name,str(pool_used),pool_used_warn) + " - " + output )
               sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
