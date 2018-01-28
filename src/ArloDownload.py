#!/usr/bin/python3
#
# ArloDownload - A video backup utility for the Netgear Arlo System
#
# Version 3.0
#
# Contributors:
#  Janick Bergeron <janick@bergeron.com>
#  Preston Lee <zettaiyukai@gmail.com>
#  Tobias Himstedt <himstedt@gmail.com>
#  Anthony Ferrario <anthony.ferrario@gmail.com>
#  Dale Ferrario <daleferrario@gmail.com
#
# Requirements:
#  Python 3
#  Dropbox Python SDK
#
# This script is open-source; please use and distribute as you wish.
# There are no warranties; please use at your own risk.
#
# Master GIT repository: git@github.com:janick/ArloDownload.git
#

import argparse
import configparser
import os
import psutil
import signal
import sys
import time
# local imports
from arloConnector import arloConnector
from localBackend import localBackend
# from dropboxBackend import dropboxBackend
from driveBackend import driveBackend

# Parse command-line options
parser = argparse.ArgumentParser()
# Make the debug mode default to avoid clobberring a running install
parser.add_argument('-X', action='store_const', const=0, dest='debug', default=0, help='debug mode')
args = parser.parse_args()

# Parse config file
config = configparser.ConfigParser()
#config.read('/etc/systemd/arlo.conf')
config.read(os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..','arlo.conf')))
rootdir = config['Default']['rootdir']

# In debug mode, do not interfere with the regular data files
if args.debug:
    rootdir = rootdir + ".debug"
if not os.path.exists(rootdir):
    os.makedirs(rootdir)

# Check if another instance is already running
lock = os.path.join(rootdir, "ArloDownload.pid")
if os.path.isfile(lock):
    pid = int(open(lock, 'r').read())
    if pid == 0:
        print(lock + " file exists but connot be read. Assuming an instance is already running. Exiting.")
        sys.exit(1)
        
    if psutil.pid_exists(pid):
        # if the lock file is more than a few hours old, we got ourselves something hung...
        if ((time.time() - os.path.getmtime(lock)) < 60*60*6):
            print("An instance is already running. Exiting.")
            sys.exit(1)
        print("Process " + str(pid) + " appears stuck. Killing it.")
        os.kill(pid, signal.SIGTERM);
        time.sleep(1)
        if psutil.pid_exists(pid):
            print("ERROR: Unable to kill hung process. Exiting.")
            sys.exit(1)
        # We can proceed and claim this run as our own...


# I guess something crashed. Let's go ahead and claim this run!
open(lock, 'w').write(str(os.getpid()))

# Setup backend and scratch space
if not args.debug:
    if 'dropbox.com' in config and 'token' in config['dropbox.com']:
        pass
        # backend = dropboxBackend(config)
    elif 'drive.google.com' in config:
        backend = driveBackend(config)
else:
    backend = localBackend(rootdir)

arlo = arloConnector(config)
arlo.backupLibrary(backend)
print('Done!')
os.unlink(lock)
