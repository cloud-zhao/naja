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

class MyError(Exception):
        def __init__(self,msg):
                Exception.__init__(self)
                self.msg=msg
class SysProcError(MyError):
	pass
class ConfigFileError(MyError):
	pass
class ConfigFieldError(MyError):
	pass



