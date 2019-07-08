#!/usr/bin/env python
# 
# ======================= SUMMARY ================================
#
# Program : check_redis.py
# Version : 0.1
# Date    : Jul 07, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_redis.py -H 127.0.0.1 -p 6379 -T 0.1 0.2 -S 3600 86400
# OK - redis 5.0.5 on 127.0.0.1:6379, up 0 days, 20 hours, 35 minutes | response_time=0.003674;0.1;0.2;0.000000 used_memory=1667072 hit_rate=100
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_redis
#    command_line    $USER1$/check_redis.py -H $HOSTADDRESS$ -p $ARG1$ -T $ARG2$ -S $ARG3$ $ARG4$
# }
#
# Arguments and thresholds are:
#  ARG1 : Port
#  ARG2 : Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
#  ARG3 : Last DB Save Threshold. Below it is  >3600s for WARNING, >86400s for critical
#
# define service {
#       use                     prod-service
#       service_description     Redis: Port 6379
#       check_command           check_memcached!6379!0.1 0.2!!3600 86400
#       hostgroups              memcached
# }
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Jul 2019] First version of the code.
#
#
#  TODO
#     (a) Add option to check from master that slave is connected and working.
#     (b) Look into replication delay from master and how it can be done. Look
#         for into on replication_delay from slave as well
#     (c) How to better calculate memory utilization and get max memory available
#         without directly specifying it
#
# ============================ START OF PROGRAM CODE =============================
#
# sudo pip install redis | sudo easy_install redis
# https://pypi.org/project/redis/

import argparse
import logging
import os, sys, time
import redis

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

def convert_to_days(seconds):
    """Return the tuple of days, hours, minutes and seconds."""

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return "%s days, %s hours, %s minutes" % (days, hours, minutes)


def get_args(): 
   """
   Supports the command-line arguments listed below. 
   """
   parser = argparse.ArgumentParser(description="Redis Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 6379)', dest='port', type=str, default=['6379'])

   parser.add_argument('-T', nargs=2, required=False, help='Measure the output connection response time in seconds -T [WARN,CRIT] \n Ex.: -T 0.1 0.5', dest='response_time', type=str)
   parser.add_argument('-S', nargs=2, required=False, help='Check the number of seconds since the last save -S [WARN,CRIT]. Ex. -S 3600 86400', dest='last_save_time', type=str)

   parser.add_argument('-t', nargs=1, required=False, help='Connection TimeOut', dest='timeout', type=int)
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

   if args.last_save_time:
      last_save_time_warn   = args.last_save_time[0]
      last_save_time_crit   = args.last_save_time[1]

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
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s TIMEOUT: %s" % (host,port,timeout))
     start = time.time()
     client = redis.Redis(host=host,port=port,socket_timeout=timeout)
     stats = client.info()
     #mylogger.debug(stats)
     end = time.time()

     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (stats is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)

   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)


   #Redis info
   uptime = stats["uptime_in_seconds"]
   uptime_days = convert_to_days(int(uptime))
   version = stats["redis_version"]
  
   redis_info="redis %s on %s:%s, up %s" % (version,host,port,uptime_days)

   #
   used_memory = stats["used_memory_rss"]
   evicted_keys = stats["evicted_keys"]
   connected_clients = stats["connected_clients"]
   rdb_last_save_time = stats["rdb_last_save_time"]
   mylogger.debug("rdb_last_save_time %s" % (rdb_last_save_time))

   #hit rate
   keyspace_hits = stats["keyspace_hits"]
   keyspace_misses = stats["keyspace_misses"]
   mylogger.debug("keyspace_hits: %s keyspace_misses: %s" % (keyspace_hits,keyspace_misses))
   try:
       hit_rate = round( float(keyspace_hits) * 100 / float(keyspace_hits + keyspace_misses), 2)
   except ZeroDivisionError:
       hit_rate = 100
   
   ############
   #perfdata
   ###########

   #responde_time
   resp_warn_data = ""
   resp_crit_data = ""
   if args.response_time:
      resp_warn_data = round(float(response_warn), 6)
      resp_crit_data = round(float(response_crit), 6)
   resp_time_data = str(resp_time) + ";" + str(resp_warn_data) + ";" + str(resp_crit_data) + ";0.000000"


   perfdata= "response_time=%s used_memory=%s hit_rate=%s connections=%s evicted_keys=%s" % (resp_time_data,used_memory,hit_rate,connected_clients,evicted_keys)

   output = redis_info + " | " + perfdata;

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

   #last_save_time
   if args.last_save_time:
	   last_save_time = time.time() - rdb_last_save_time
	   mylogger.debug("Last Save Time:%s -  WARN: %s, CRIT %s " % (last_save_time,last_save_time_warn,last_save_time_crit) )

	   if (int(last_save_time) >= int(last_save_time_crit)) :
	       mylogger.critical("last_save_time %s > %s" % (last_save_time,last_save_time_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (int(last_save_time) >= int(last_save_time_warn)) :
	       mylogger.warning("last_save_time %s > %s" % (last_save_time,last_save_time_warn) + " - " + output )
	       sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)


if __name__ == "__main__":
   main()
