#!/usr/bin/env python
#
# ======================= SUMMARY ================================
#
# Program : basic_encode.py
# Version : 0.1
# Date    : Sep 02, 2019
# Author  : Jan Souza - me@jansouza.com
#
# Command line Ex.: ./basic_encode.py -u username -a password
#

import argparse
import logging
import os, sys, time

import requests, base64

def get_args():

   parser = argparse.ArgumentParser(description="Basic Authorization Encode")
   parser._optionals.title = "Options"

   parser.add_argument('-u', nargs=1, required=True, help='Username', dest='username', type=str)
   parser.add_argument('-p', nargs=1, required=True, help='Password', dest='password', type=str)

   args = parser.parse_args()
   return args


def main():
    # Handling arguments
    args = get_args()

    #authentication
    username = args.username[0]
    password = args.password[0]

    auth_str = '%s:%s' % (username, password)
    b64_auth_str = base64.encodestring(auth_str)

    print "username: %s" % username
    print "password: %s" % password
    print "Encoder: %s" % b64_auth_str

if __name__ == "__main__":
   main()
