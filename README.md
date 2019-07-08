Nagios-plugins
=====================================

# Description

This project have some scripts that i wrote to monitoring Middleware services at Nagios.

## Memcached Check plugin
This is Memcached Check plugin. It gets stats variables and allows to set thresholds
on their value. It can measure response time, calculate hitrate, memory utilization and other data.

Used:
```
usage: check_memcached.py [-h] [-H HOST] [-p PORT]
                          [-T RESPONSE_TIME RESPONSE_TIME]
                          [-U UTILIZATION UTILIZATION] [-t TIMEOUT] [-v]

Memcache Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 11211)
  -T RESPONSE_TIME RESPONSE_TIME
                        Measure the output connection response time in seconds
                        -T [WARN,CRIT] Ex.: -T 0.1 0.5
  -U UTILIZATION UTILIZATION
                        This calculates percent of space in use, which is
                        bytes/limit_maxbytes -U [WARN,CRIT] Ex.: -U 95 98
  -t TIMEOUT            Connection TimeOut
  -v, --verbose         Enable verbose output

Ex.:
   Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
   Utilization/Size Threshold. Below it is >95% for warning, >98% for critical
   ./check_memcached.py -H 127.0.0.1 -p 11211 -T 0.1 0.2 -U 95 98
   
```

#### Memcached - PNP4Nagios
This plugin also collection information about performance data from memcached server, that can be used by PNP4Nagios
   
   - response_time
   - hit_rate
   - curr_connections
   - utilization
   - evictions
   
   ![memcached-response-time](https://github.com/jansouza/nagios-plugins/blob/master/images/memcached-response_time.jpg)
   ![memcached-hit_rate](https://github.com/jansouza/nagios-plugins/blob/master/images/memcached-hitrate.jpg)
   
## Redis Check plugin
This plugin checks Redis status, measures its response time and if specified allows to set thresholds on one or more key data

Used:
```
usage: check_redis.py [-h] [-H HOST] [-p PORT]
                      [-T RESPONSE_TIME RESPONSE_TIME]
                      [-S LAST_SAVE_TIME LAST_SAVE_TIME] [-t TIMEOUT] [-v]

Redis Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 6379)
  -T RESPONSE_TIME RESPONSE_TIME
                        Measure the output connection response time in seconds
                        -T [WARN,CRIT] Ex.: -T 0.1 0.5
  -S LAST_SAVE_TIME LAST_SAVE_TIME
                        Check the number of seconds since the last save -S
                        [WARN,CRIT]. Ex. -S 3600 86400
  -t TIMEOUT            Connection TimeOut
  -v, --verbose         Enable verbose output
   
```
   
#### Redis - PNP4Nagios
This plugin also collection information about performance data from memcached server, that can be used by PNP4Nagios
   
   - response_time
   - used_memory
   - hit_rate
   - connections
   - evicted_keys
   
   ![redis-response-time](https://github.com/jansouza/nagios-plugins/blob/master/images/redis-response_time.jpg)
   ![redis-used_memory](https://github.com/jansouza/nagios-plugins/blob/master/images/redis-used_memory.jpg)
   
