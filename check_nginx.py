#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_nginx.py
# Version : 0.3
# Date    : Jul 07, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_nginx.py -H 127.0.0.1 -p 80 -u /nginx_status
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_nginx
#    command_line    $USER1$/check_nginx.py -H $HOSTADDRESS$ -u $ARG1$ -T $ARG2$ -C $ARG3$ $ARG4$
# }
#
# Arguments and thresholds are:
#  ARG1 : Status URL
#  ARG2 : Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
#  ARG3 : Current Connections Threshold. Below it is >30 for warning, >50 for critical
#
# define service {
#       use                     prod-service
#       service_description     NGINX STATUS
#       check_command           check_nginx!/status!0.1 0.2!!30 50
#       hostgroups              nginx
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Jul 2019] First version of the code.
#  [0.2 - Sep 2019] Fix request timeout
#  [0.3 - May 2020] Fix Request Log Level
#
#  TODO
#     (a)
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
   parser = argparse.ArgumentParser(description="NGINX Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 80)', dest='port', type=str, default=['80'])
   parser.add_argument('-u', nargs=1, required=True, help='Status URL Context', dest='context', type=str)

   parser.add_argument('-T', nargs=2, required=False, help='Measure the output connection response time in seconds -T [WARN,CRIT] \n Ex.: -T 0.1 0.5', dest='response_time', type=str)
   parser.add_argument('-C', nargs=2, required=False, help='Measure the number of clients connections currently -C [WARN,CRIT] \n Ex.: -C 30 50', dest='current_conn', type=str)

   parser.add_argument('--ssl', required=False, help='Enable SSL Request', dest='ssl', action='store_true')

   parser.add_argument('-t', nargs=1, required=False, help='Connection Timeout', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args


def main():
   # Handling arguments
   args = get_args()

   host = args.host[0]
   port = args.port[0]

   if args.response_time:
       response_warn   = args.response_time[0]
       response_crit   = args.response_time[1]

   if args.current_conn:
       current_conn_warn   = args.current_conn[0]
       current_conn_crit   = args.current_conn[1]

   #url
   context = args.context[0]

   ssl = args.ssl
   if ssl:
       port = "443"

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

   resp_time=0
   status = {}
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s CONTEXT: %s TIMEOUT: %s" % (host,port,context,timeout))
     start = time.time()

     url = "http://"
     if ssl:
       url = "https://"

     url += host + ":" + port + context
     mylogger.debug("URL: %s" % (url))
     res = requests.get(url, verify=False, timeout=timeout)

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

   lines = html.split('\n')

   _, value = lines[0].split(':')
   # server accepts handled requests
   #  16462 16462 28543
   status['active'] = int(value)

   accepts, handled, request = [int(v) for v in lines[2].split()]
   status['accepts'] = accepts
   status['handled'] = handled
   status['requests'] = request

   # Reading: 0 Writing: 1 Waiting: 4
   values = lines[3].split()
   reading, writing, waiting = [int(v) for v in values[1:6:2]]
   status['reading'] = reading
   status['writing'] = writing
   status['waiting'] = waiting

   mylogger.debug(status)

   try:
       requests_per_conn = round( float(request) / float(handled), 2)
   except ZeroDivisionError:
       requests_per_conn = 0.0

   ############
   #perfdata
   ###########
   active = status['active']

   #response_time
   resp_warn_data = ""
   resp_crit_data = ""
   if args.response_time:
      resp_warn_data = round(float(response_warn), 6)
      resp_crit_data = round(float(response_crit), 6)
   resp_time_data = str(resp_time) + ";" + str(resp_warn_data) + ";" + str(resp_crit_data) + ";0.000000"

   #Currnet Connections
   conn_warn_data = ""
   conn_crit_data = ""
   if args.current_conn:
      conn_warn_data = current_conn_warn
      conn_crit_data = current_conn_crit
   current_conn_data = str(active) + ";" + str(conn_warn_data) + ";" + str(conn_crit_data) + ";0"

   perfdata = "response_time=%s active=%s requests_per_conn=%s" % (resp_time_data,current_conn_data,requests_per_conn)

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

   #Current Connections
   if args.current_conn:
	   mylogger.debug("Current Connections WARN: %s, CRIT %s " % (current_conn_warn,current_conn_crit) )

	   if (active >= int(current_conn_crit)) :
	       mylogger.critical("Current Connections %s > %s" % (active,current_conn_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (active >= int(current_conn_warn)) :
	       mylogger.warning("Current Connections %s > %s" % (active,current_conn_warn) + " - " + output )
	       sys.exit(WARNING)


   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
