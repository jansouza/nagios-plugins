#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : check_memcached.py
# Version : 0.2
# Date    : Jul 07, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./check_memcached.py -H 127.0.0.1 -p 11211 -T 0.1 0.2 -U 95 98
# OK - memcached 1.5.16 on 127.0.0.1:11211, up 4 days, 0 hours, 16 minutes | response_time=0.008573;0.1;0.2;0.000000 hit_rate=8.38 curr_connections=2 utilization=0.0;95.0;98.0;0.00 evictions=0
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command {
#    command_name    check_memcached
#    command_line    $USER1$/check_memcached.py -H $HOSTADDRESS$ -p $ARG1$ -T $ARG2$ -U $ARG3$
# }
#
# Arguments and thresholds are:
#  ARG1 : Port
#  ARG2 : Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
#  ARG3 : Utilization/Size Threshold. Below it is >95% for warning, >98% for critical
#
# define service {
#       use                     prod-service
#       service_description     Memcached: Port 11212
#       check_command           check_memcached!11212!0.1 0.2!!95 98
#       hostgroups              memcached
# }
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Jul 2019] First version of the code.
#  [0.2 - sep 2019] Include debug to telnetlib
#
#
#  TODO
#     (a) Support SASL Authentication
#
# ============================ START OF PROGRAM CODE =============================

import argparse
import logging
import os, sys, time
import re, telnetlib

# NAGIOS return codes :
# https://nagios-plugins.org/doc/guidelines.html#AEN78
OK       = 0
WARNING  = 1
CRITICAL = 2
UNKNOWN  = 3

mylogger = logging.getLogger(__name__)

class MemcachedStats:

    _client = None
    _key_regex = re.compile(r'ITEM (.*) \[(.*); (.*)\]')
    _slab_regex = re.compile(r'STAT items:(.*):number')
    _stat_regex = re.compile(r"STAT (.*) (.*)\r")

    def __init__(self, host='localhost', port='11211', timeout=None, log_level=0):
        self._host = host
        self._port = port
        self._timeout = timeout
        self.log_level = log_level

    @property
    def client(self):
        if self._client is None:
            self._client = telnetlib.Telnet(self._host, self._port,self._timeout)
            self._client.set_debuglevel(self.log_level)
        return self._client

    def command(self, cmd):
        ' Write a command to telnet and return the response '
        self.client.write(("%s\n" % cmd).encode('ascii'))
        return self.client.read_until(b'END').decode('ascii')

    def key_details(self, sort=True, limit=100):
        ' Return a list of tuples containing keys and details '
        cmd = 'stats cachedump %s %s'
        keys = [key for id in self.slab_ids()
            for key in self._key_regex.findall(self.command(cmd % (id, limit)))]
        if sort:
            return sorted(keys)
        else:
            return keys

    def keys(self, sort=True, limit=100):
        ' Return a list of keys in use '
        return [key[0] for key in self.key_details(sort=sort, limit=limit)]

    def slab_ids(self):
        ' Return a list of slab ids in use '
        return self._slab_regex.findall(self.command('stats items'))

    def stats(self):
        ' Return a dict containing memcached stats '
        return dict(self._stat_regex.findall(self.command('stats')))

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
   parser = argparse.ArgumentParser(description="Memcache Check for Nagios")
   parser._optionals.title = "Options"

   parser.add_argument('-H', nargs=1, required=False, help='Hostname or IP Address to check', dest='host', type=str, default=['127.0.0.1'])
   parser.add_argument('-p', nargs=1, required=False, help='port number (default: 11211)', dest='port', type=str, default=['11211'])

   parser.add_argument('-T', nargs=2, required=False, help='Measure the output connection response time in seconds -T [WARN,CRIT] \n Ex.: -T 0.1 0.5', dest='response_time', type=str)
   parser.add_argument('-U', nargs=2, required=False, help='This calculates percent of space in use, which is bytes/limit_maxbytes -U [WARN,CRIT] \n Ex.: -U 95 98', dest='utilization', type=str)

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

   if args.utilization:
      utilization_warn   = args.utilization[0]
      utilization_crit   = args.utilization[1]

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
   telnet_debug = 0
   if (verbose):
     telnet_debug = 1

   resp_time=0
   try:
     mylogger.debug("Get Stats - HOSTNAME: %s PORT: %s TIMEOUT: %s" % (host,port,timeout))
     start = time.time()

     mem = MemcachedStats(host, port, timeout,telnet_debug)
     stats = mem.stats()
     end = time.time()
     response_time = end - start
     resp_time = round(float(response_time), 6)

     if (stats is None) :
        mylogger.unkown("response_time %s" % resp_time)
        sys.exit(UNKNOWN)


   except Exception as ex:
     mylogger.critical(ex)
     sys.exit(CRITICAL)

   #memcache_info
   uptime = stats["uptime"]
   uptime_days = convert_to_days(int(uptime))
   version = stats["version"]

   #hit_rate
   get_hits = stats["get_hits"]
   get_misses = stats["get_misses"]
   cmd_get = stats["cmd_get"]
   mylogger.debug("get_hits: %s get_misses: %s cmd_get: %s " % (get_hits,get_misses,cmd_get))
   try:
       hit_rate = round( float(get_hits) * 100 / float(cmd_get), 2)
   except ZeroDivisionError:
       hit_rate = 100

   #utilization
   bytes = stats["bytes"]
   limit_maxbytes = stats["limit_maxbytes"]
   utilization = round( float(bytes) * 100 / float(limit_maxbytes), 2);
   mylogger.debug("bytes: %s limit_maxbytes: %s" % (bytes,limit_maxbytes))

   #others
   evictions = stats["evictions"]
   curr_connections = stats["curr_connections"]

   #output
   memcache_info="memcached %s on %s:%s, up %s" % (version,host,port,uptime_days)

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

   #Utilization
   uti_warn_data = ""
   uti_crit_data = ""
   if args.response_time:
      uti_warn_data = round(float(utilization_warn), 2)
      uti_crit_data = round(float(utilization_crit), 2)
   uti_data = str(utilization) + ";" + str(uti_warn_data) + ";" + str(uti_crit_data) + ";0.00"

   perfdata= "response_time=%s hit_rate=%s curr_connections=%s utilization=%s evictions=%s" % (resp_time_data,hit_rate,curr_connections,uti_data,evictions)

   output = memcache_info + " | " + perfdata;

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

   #Utilization
   if args.utilization:
	   mylogger.debug("Utilization WARN: %s, CRIT %s " % (utilization_warn,utilization_crit) )

	   uti_warn = round(float(utilization_warn), 2)
	   uti_crit = round(float(utilization_crit), 2)

	   if (utilization >= uti_crit) :
	       mylogger.critical("utilization %s > %s" % (utilization,uti_crit) + " - " + output )
	       sys.exit(CRITICAL)
	   elif (utilization >= uti_warn) :
	       mylogger.warning("utilization %s > %s" % (utilization,uti_warn) + " - " + output )
	       sys.exit(WARNING)

   mylogger.info(output)
   sys.exit(OK)

if __name__ == "__main__":
   main()
