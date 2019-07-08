#!/bin/sh
#
# ======================= SUMMARY ================================
#
# Program : check_by_socks.sh
# Version : 0.1
# Date    : Set 12, 2014
# Author  : Jan Souza - me@jansouza.com
# Description: Nagios Check by Socks
# Usage: check_by_socks.sh nagios_cmd "nagios_param"
#set +x
#
# ======================= NAGIOS CONFIGURATION =====================
#
# 1. Example of Nagios Config Definitions
#
# A. Sample command and service definitions
#
# define command{
#        command_name    check_memcached_socks
#        command_line    $USER1$/check_by_socks.sh check_memcached.py "-H $HOSTADDRESS$ -p $ARG1$ $ARG2$ -t 5"
#        }
#
# ======================= VERSION HISTORY and TODO ================================
#
#
#  [0.1 - Set 2014] First version of the code.
#
#
#  TODO
#
# ============================ START OF PROGRAM CODE =============================

export TSOCKS_CONF_FILE=/etc/socks.conf
export TSOCKS_USERNAME=
export TSOCKS_PASSWORD=
#export TSOCKS_DEBUG=-1
export TSOCKS_DEBUG=1
export TSOCKS_DEBUG_FILE=/tmp/tsocks.log

export NAGIOS_PATH=/usr/local/nagios/libexec
export TSOCKS_PATH=/usr/bin/tsocks

NAGIOS_CMD=$1
NAGIOS_PARAM=$2

#echo "NAGIOS_PATH: $NAGIOS_PATH"
#echo "NAGIOS_CMD: $NAGIOS_CMD"
#echo "NAGIOS_PARAM: $NAGIOS_PARAM"

$TSOCKS_PATH $NAGIOS_PATH/$NAGIOS_CMD $NAGIOS_PARAM
exit $?
