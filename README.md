Nagios-plugins
=====================================

# Description

This project have some scripts that i wrote to monitoring Middleware services at Nagios.

## Apache Check plugin
This is Apache Check plugin. It gets stats variables and allows to set thresholds
on their value. It can measure response time, current connections, idle workers and other data.

Used:
```
usage: check_apache.py [-h] [-H HOST] [-p PORT] [-u CONTEXT]
                       [-T RESPONSE_TIME RESPONSE_TIME]
                       [-C CURRENT_CONN CURRENT_CONN]
                       [-I IDLE_WORKERS_ARG IDLE_WORKERS_ARG] [--ssl]
                       [-t TIMEOUT] [-v]

APACHE Status Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 80)
  -u CONTEXT            Status URL Context
  -T RESPONSE_TIME RESPONSE_TIME
                        Measure the output connection response time in seconds
                        -T [WARN,CRIT] Ex.: -T 0.1 0.5
  -C CURRENT_CONN CURRENT_CONN
                        Measure the number of clients connections currently -C
                        [WARN,CRIT] Ex.: -C 30 50
  -I IDLE_WORKERS_ARG IDLE_WORKERS_ARG
                        Measure the number of idle workers -I [WARN,CRIT] Ex.:
                        -I 5 1
  --ssl                 Enable SSL Request
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output

Ex.:
 Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
 Current Connections Threshold. Below it is >100 for warning, >200 for critical
 Idle Workers Threshold. Below it is <30 for warning, <10 for critical
 ./check_apache.py -H 127.0.0.1 -T 0.1 0.2 -C 100 200 -I 30 10

```

#### Apache - PNP4Nagios
This plugin also collection information about performance data from apache server, that can be used by PNP4Nagios

   - response_time
   - busy_workers
   - idle_workers
   - requests_per_second
   - bytes_per_second
   - bytes_per_request

   ![apache-busy_workers](https://github.com/jansouza/nagios-plugins/blob/master/images/apache-busy_workers.jpg)
   ![apache-requests_per_second](https://github.com/jansouza/nagios-plugins/blob/master/images/apache-requests_per_second.jpg)


## Nginx Check plugin
This is Nginx Check plugin. It gets stats variables and allows to set thresholds
on their value. It can measure response time, active connections and other data.

Used:
```
usage: check_nginx.py [-h] [-H HOST] [-p PORT] -u CONTEXT
                      [-T RESPONSE_TIME RESPONSE_TIME]
                      [-C CURRENT_CONN CURRENT_CONN] [--ssl] [-t TIMEOUT] [-v]

NGINX Status Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 80)
  -u CONTEXT            Status URL Context
  -T RESPONSE_TIME RESPONSE_TIME
                        Measure the output connection response time in seconds
                        -T [WARN,CRIT] Ex.: -T 0.1 0.5
  -C CURRENT_CONN CURRENT_CONN
                        Measure the number of clients connections currently -C
                        [WARN,CRIT] Ex.: -C 30 50
  --ssl                 Enable SSL Request
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output

Ex.:
 Response Time Threshold. Below it is  >0.1s for WARNING, >0.2s for critical
 Current Connections Threshold. Below it is >100 for warning, >200 for critical
 Idle Workers Threshold. Below it is <30 for warning, <10 for critical

 ./check_nginx.py -H 127.0.0.1 -p 80 -u /nginx_status -T 0.1 0.2 -C 100 200 -I 30 10

```

#### Nginx - PNP4Nagios
This plugin also collection information about performance data from Nginx server, that can be used by PNP4Nagios

   - response_time
   - active
   - requests_per_conn

   ![nginx-active](https://github.com/jansouza/nagios-plugins/blob/master/images/nginx-active.jpg)


## Tomcat Check plugin
This is Tomcat Check plugin. It gets stats variables and allows to set thresholds
on their value. It can measure response time, memory utilization,current connections, idle workers and other data.

Used:
```
usage: check_tomcat.py [-h] [-H HOST] [-p PORT] [-U CONTEXT] -a BASIC_AUTH
                       [-T RESPONSE_TIME RESPONSE_TIME] [-M MEM_USED MEM_USED]
                       [-C THREADS_BUSY THREADS_BUSY] [-t TIMEOUT] [-v]

TOMCAT Status Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 8080)
  -U CONTEXT            Status URL Context
  -a BASIC_AUTH         Authentication (use basic_encoder.py)
  -T RESPONSE_TIME RESPONSE_TIME
                        Measure the output connection response time in seconds
                        -T [WARN,CRIT] Ex.: -T 0.1 0.5
  -M MEM_USED MEM_USED  Measure the percent of used memory heap -M [WARN,CRIT]
                        Ex.: -C 80 90
  -C THREADS_BUSY THREADS_BUSY
                        Measure the percent of Threads Busy -C [WARN,CRIT]
                        Ex.: -C 80 90
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output

Ex.:
 Response Time Threshold. Below it is >0.3s for WARNING, >0.5s for critical
 Memory Heap  Threshold. Below it is >80% for WARNING, >90% for critical
 Threads Busy Threshold. Below it is >80% for warning, >90% for critical

 ./check_tomcat.py -H 127.0.0.1 -a dG9tY2F0OnRvbWNhdA== -T 0.3 0.5 -M 80 90 -C 80 90

```

#### Tomcat - PNP4Nagios
This plugin also collection information about performance data from tomcat server, that can be used by PNP4Nagios

   - response_time
   - mem_used
   - heap_size
   - percent_thread
   - busy_thread

   ![tomcat-used_memory](https://github.com/jansouza/nagios-plugins/blob/master/images/tomcat-used_memory.jpg)


## Tomcat DBCP Check plugin
This is Tomcat DBCP (Database Connections Pool) check plugin. It gets stats variables and allows to set thresholds
on their value. It can measure database pool utilization and other data.

Used:
```
usage: check_tomcat_dbcp.py [-h] [-H HOST] [-p PORT] [-u CONTEXT] -a
                            BASIC_AUTH -j JNDI_NAME [-U POOL_USED POOL_USED]
                            [-t TIMEOUT] [-v]

TOMCAT DBCP Status Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 8080)
  -u CONTEXT            Status URL Context
  -a BASIC_AUTH         Authentication (use basic_encoder.py)
  -j JNDI_NAME          JNDI name
  -U POOL_USED POOL_USED
                        Measure the percent of used connections -U [WARN,CRIT]
                        Ex.: -U 80 90
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output


Ex.:
 Basic Authentication (use basic_encode.py)
 JNDI Name
 Database Pool Utilization Threshold. Below it is >80% for WARNING, >90% for critical
 Others arguments. Below set connections Timeout

  ./check_tomcat_dbcp.py -H 127.0.0.1 -p 8080 -a dG9tY2F0OnRvbWNhdA== -j JNDI_NAME -P 80 90 -T 30

```

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
  -t TIMEOUT            Connection Timeout
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
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output

```

#### Redis - PNP4Nagios
This plugin also collection information about performance data from Redis server, that can be used by PNP4Nagios

   - response_time
   - used_memory
   - hit_rate
   - connections
   - evicted_keys

   ![redis-response-time](https://github.com/jansouza/nagios-plugins/blob/master/images/redis-response_time.jpg)
   ![redis-used_memory](https://github.com/jansouza/nagios-plugins/blob/master/images/redis-used_memory.jpg)

## Apache Solr Check plugin
This plugin checks Apache Solr status, measures memory heap utilization and if specified allows to set thresholds on one or more key data

Used:
```
usage: check_solr.py [-h] [-H HOST] [-p PORT] [-a BASIC_AUTH]
                     [-M MEM_USED MEM_USED] [-t TIMEOUT] [-v]

Apache Solr Status Check for Nagios

Options:
  -h, --help            show this help message and exit
  -H HOST               Hostname or IP Address to check
  -p PORT               port number (default: 8983)
  -a BASIC_AUTH         Authentication (use basic_encoder.py)
  -M MEM_USED MEM_USED  Measure the percent of used memory heap -M [WARN,CRIT]
                        Ex.: -C 80 90
  -t TIMEOUT            Connection Timeout
  -v, --verbose         Enable verbose output

```

#### Apache Solr - PNP4Nagios
This plugin also collection information about performance data from Apache Solr server, that can be used by PNP4Nagios

   - heap_percent_used
   - heap_used

   ![solr-heap_percent_used](https://github.com/jansouza/nagios-plugins/blob/master/images/solr-heap_percent_used.jpg)
   
