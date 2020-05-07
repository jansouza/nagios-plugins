#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_apache.py
# Version : 0.4
# Date    : Jul 07, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_apache.py -H 127.0.0.1
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_apache_status
#    command_line    $USER1$/check_apache.py -H $HOSTADDRESS$ -u $ARG1$ -T $ARG2$ -C $ARG3$ -I $ARG4$ $ARG5$
# }
#
# Arguments and thresholds are:
#  ARG1 : Status URL
#  ARG2 : Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
#  ARG3 : Current Connections Threshold. Below it is >100 for warning, >200 for critical
#  ARG4 : Idle Workers Threshold. Below it is <30 for warning, <10 for critical
#
# define service {
#       use                     prod-service
#       service_description     APACHE STATUS
#       check_command           check_apache!/server-status!0.1 0.2!!100 200!30 10!
#       hostgroups              apache
# }
#
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Jul 2019] First version of the code.
#  [0.2 - Sep 2019] Fix request timeout | Fix get no status page
#  [0.3 - Apr 2020] Fix SSL port
#  [0.4 - May 2020] Fix Request Log Level
#
#
#  TODO
#     (a)
#
# ============================ START OF PROGRAM CODE =============================
# sudo pip install requests | sudo easy_install requests | https://pip.pypa.io/en/stable/installing/
# https://pypi.org/project/requests/

import argparse
import logging
import os, sys, time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import re

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
   parser = argparse.ArgumentParser(description="APACHE Status Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 80)', dest='port', type=str, default=['80'])
   parser.add_argument('-u', nargs=1, required=False, help='Status URL Context', dest='context', type=str, default=['/server-status'])

   parser.add_argument('-T', nargs=2, required=False, help='Measure the output connection response time in seconds -T [WARN,CRIT] \n Ex.: -T 0.1 0.5', dest='response_time', type=str)
   parser.add_argument('-C', nargs=2, required=False, help='Measure the number of clients connections currently -C [WARN,CRIT] \n Ex.: -C 30 50', dest='current_conn', type=str)
   parser.add_argument('-I', nargs=2, required=False, help='Measure the number of idle workers -I [WARN,CRIT] \n Ex.: -I 5 1', dest='idle_workers_arg', type=str)

   parser.add_argument('--ssl', required=False, help='Enable SSL Request', dest='ssl', action='store_true')

   parser.add_argument('-t', nargs=1, required=False, help='Connection Timeout', dest='timeout', type=int)
   parser.add_argument('-v', '--verbose', required=False, help='Enable verbose output', dest='verbose', action='store_true')

   args = parser.parse_args()
   return args

def convert_to_days(seconds):
    """Return the tuple of days, hours, minutes and seconds."""

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return "%s days, %s hours, %s minutes" % (days, hours, minutes)

def parserStatus(html):
    parsed = {
              'server_version':None,
              'total_accesses': None,
              'total_kbytes': None,
              'cpuload': None,
              'uptime': None,
              'requests_per_second': None,
              'bytes_per_second': None,
              'bytes_per_request': None,
              'busy_workers': None,
              'idle_workers': None,
              'waiting_for_connection': None,
              'starting_up': None,
              'reading_request': None,
              'sending_reply': None,
              'keepalive': None,
              'dns_lookup': None,
              'closing_connection': None,
              'logging': None,
              'gracefully_finishing': None,
              'idle_cleanup_of_worker': None,
              'open_slots': None}

    key_count = 0
    for line in html.splitlines():
       items = line.split(': ')

       if (items and len(items) != 2):
           continue

       key = items[0]
       value = items[1]

       if key == 'ServerVersion':
           parsed['server_version'] = str(value)
           key_count += 1
       if key == 'Total Accesses':
            parsed['total_accesses'] = int(value)
            key_count += 1
       if key == 'Total Accesses':
            parsed['total_accesses'] = int(value)
            key_count += 1
       if key == 'Total kBytes':
            parsed['total_kbytes'] = int(value)
            key_count += 1
       if key == 'CPULoad':
            parsed['cpuload'] = float(value)
            key_count += 1
       if key == 'Uptime':
            parsed['uptime'] = int(value)
            key_count += 1
       if key == 'ReqPerSec':
            parsed['requests_per_second'] = float(value)
            key_count += 1
       if key == 'BytesPerSec':
            parsed['bytes_per_second'] = float(value)
            key_count += 1
       if key == 'BytesPerReq':
           parsed['bytes_per_request'] = float(value)
           key_count += 1
       if key == 'BusyWorkers':
            parsed['busy_workers'] = int(value)
            key_count += 1
       if key == 'IdleWorkers':
            parsed['idle_workers'] = int(value)
            key_count += 1
       if key == 'Scoreboard':
            parsed['waiting_for_connection'] = value.count('_')
            parsed['starting_up'] = value.count('S')
            parsed['reading_request'] = value.count('R')
            parsed['sending_reply'] = value.count('W')
            parsed['keepalive'] = value.count('K')
            parsed['dns_lookup'] = value.count('D')
            parsed['closing_connection'] = value.count('C')
            parsed['logging'] = value.count('L')
            parsed['gracefully_finishing'] = value.count('G')
            parsed['idle_cleanup_of_worker'] = value.count('I')
            parsed['open_slots'] = value.count('.')
            key_count += 1

    if (key_count < 3):
       return None
    else:
       return parsed

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

   if args.idle_workers_arg:
       idle_workers_warn   = args.idle_workers_arg[0]
       idle_workers_crit   = args.idle_workers_arg[1]

   #url
   context = args.context[0]

   ssl = args.ssl
   if ssl and port == "80" :
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
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s CONTEXT: %s TIMEOUT: %s" % (host,port,context,timeout))
     start = time.time()

     url = "http://"
     if ssl:
       url = "https://"

     url += host + ":" + port + context + "?auto"
     mylogger.debug("URL: %s" % (url))
     res = requests.get(url, verify=False, timeout=timeout)
     end = time.time()
     mylogger.debug("STATUS_CODE: %s" % (res.status_code))

     if res.status_code != 200:
        mylogger.critical(str(res.status_code) + " Found")
        sys.exit(CRITICAL)

     stats = parserStatus(res.text)

     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (stats is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   #Apache Info
   version = stats['server_version']
   uptime = stats['uptime']
   uptime_days = convert_to_days(int(uptime))

   #Metrics
   busy_workers = stats['busy_workers']
   idle_workers = stats['idle_workers']
   requests_per_second = stats['requests_per_second']
   bytes_per_second = stats['bytes_per_second']
   bytes_per_request = stats['bytes_per_request']

   apache_info="%s on %s:%s, up %s" % (version,host,port,uptime_days)

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

   #Current Connections
   conn_warn_data = ""
   conn_crit_data = ""
   if args.current_conn:
      conn_warn_data = current_conn_warn
      conn_crit_data = current_conn_crit

   current_conn_data = str(busy_workers) + ";" + str(conn_warn_data) + ";" + str(conn_crit_data) + ";0"

   perfdata = "response_time=%s busy_workers=%s idle_workers=%s requests_per_second=%s bytes_per_second=%s bytes_per_request=%s" % (resp_time_data,current_conn_data,idle_workers,requests_per_second,bytes_per_second,bytes_per_request)

   output = apache_info + " | " + perfdata

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

	   if (busy_workers >= int(current_conn_crit)) :
	       mylogger.critical("Current Connections %s > %s" % (busy_workers,current_conn_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (busy_workers >= int(current_conn_warn)) :
	       mylogger.warning("Current Connections %s > %s" % (busy_workers,current_conn_warn) + " - " + output )
	       sys.exit(WARNING)

   #idle_workers_arg
   if args.idle_workers_arg:
	   mylogger.debug("idle_workers WARN: %s, CRIT %s " % (idle_workers_warn,idle_workers_crit) )

	   if (idle_workers <= int(idle_workers_crit)) :
	       mylogger.critical("idle_workers %s < %s" % (idle_workers,idle_workers_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (idle_workers < int(idle_workers_warn)) :
	       mylogger.warning("idle_workers %s < %s" % (idle_workers,idle_workers_warn) + " - " + output )
	       sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
