import os
import pwd
import sys
import time
import uuid
import copy
import datetime
import logging
import socket
import fcntl
import struct
import json
import urllib
import urllib2
import threading
from naja.plugin import TRun


#class TRun(MyPlugin):
#	def get_sleep(self):
#		return 0
#	def get_schedule(self):
#		return 0


class MyTestTRun(TRun):
	def run(self):
		time.sleep(2)
		print "MyTestTRun.run() wait 2 sec"
