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
from naja.error import SysProcError,ConfigFileError


class MyTools(object):
	@staticmethod
	def get_abs_path(p):
		return os.path.split(os.path.realpath(p))[0]

	@staticmethod
	def get_uuid(constant=False):
		uuid_file="%s/.naja.uuid" %(MyTools.get_abs_path(__file__))
		uuid_str=str(uuid.uuid1())
		if not constant:
			return uuid_str

		if os.path.exists(uuid_file):
			uuid_str=MyTools.head(uuid_file)[0]
		else:
			MyTools.write_file(uuid_file,uuid_str)
		return uuid_str
	
	@staticmethod
	def get_netcard():  
	    netcard_info = []  
	    info = psutil.net_if_addrs()
	    for k,v in info.items():  
	        for item in v:  
	            if item[0] == 2 and not item[1]=='127.0.0.1':  
	                netcard_info.append((k,item[1]))  
	    return netcard_info  

	@staticmethod
	def write_file(filename,ctx):
		with open(filename,'w') as fh:
			fh.write(ctx)

	@staticmethod
	def head(filename,num=1):
		lines=[]
		with open(filename,'r') as fh:
			for i in range(num):
				lines.append(fh.readline().strip())
		return lines

	@staticmethod
	def get_ip(ifName):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			ip=socket.inet_ntoa(fcntl.ioctl(
				s.fileno(),
				0x8915,
				struct.pack('256s',ifName[:15])
			)[20:24])
		except IOError,e:
			if e.errno == 19:
				ip='0.0.0.0'
		return ip

	@staticmethod
	def get_hostname():
		return socket.gethostname()

	@staticmethod
	def get_user():
		return pwd.getpwuid(os.getuid())[0]

	@staticmethod
	def basename(pathStr,suffix='',sp=None):
		string=os.path.basename(pathStr)
		if sp:
			return string.split(sp)[0]
		else:
			return string[:len(string)-len(suffix)]


class SysPs(object):
	ppath="/proc"
	cmd="cmdline"

	def __init__(self):
		if not os.path.isdir(self.ppath):
			raise SysProcError("/proc not exists")
			

	def _get_pid(self):
		command={}
		for i in os.listdir(self.ppath):
			if i.isdigit():
				try:
					fh=open(self.ppath+"/"+i+"/"+self.cmd,"r")
					command[int(i)]=fh.read()
				except:
					pass
				finally:
					if fh:
						fh.close()
		return command

	def get_process(self,pid=None,cmd=None):
		if pid == None and cmd == None:
			return {}

		clist=self._get_pid()
		if pid != None and pid in clist:
			return {pid:clist[pid].split(chr(0))}
		elif cmd != None:
			res={}
			for i in clist.keys():
				conditionList=cmd.split('|')
				conditionNum=0
				for c in conditionList:
					if clist[i].find(c) > -1:
						conditionNum += 1
				if conditionNum == len(conditionList):
					res[i]=clist[i].split(chr(0))
			return res
		else:
			return {}

	def all(self):
		clist=self._get_pid()
		rc={}
		for i in clist.keys():
			#print "Pid: %s %s" % (i," ".join(clist[i].split(chr(0))))
			rc[i]=clist[i].split(chr(0))
		return rc

	def check_active(self,pid):
		clist=self._get_pid()
		if pid in clist:
			try:
				if MyTools.get_user() == "root":
					os.kill(pid,0)
				return True
			except OSError:
				return False
		else:
			return False

class Properties(object):

	def __init__(self,configFile):
		if not os.path.isfile(configFile):
			raise ConfigFileError("%s configur file error" % (configFile))
		self.conf=configFile
		self.config={}
		self._load_proper()
		self._analysis_key()

	def _load_proper(self):
		try:
			fh=open(self.conf,"r")
			for i in fh:
				i=i.strip()
				if not i or i[0] == "#":
					continue
				s=i.split('=')
				self.config[s[0].strip()]=self._analysis_value(s[1])
		except IOError,e:
			print e
		finally:
			if fh:
				fh.close()

	def _analysis_value(self,value):
		if value.find(':') > -1:
			res={}
			for j in value.split(','):
				k,v=j.split(':')
				res[k.strip()]=v.strip()
		elif value.find(',') > -1:
			res=map(lambda v:v.strip(),value.split(','))
		else:
			res=value.strip()
		return res

	def _analysis_key(self):
		config=self.config
		self.config={}
		for k,v in config.items():
			tmp=self.config
			ks=k.split('.')
			for ik in ks[:-1]:
				tmp=tmp.setdefault(ik,{})
			tmp[ks[-1]]=v

	def get_value(self,key,default=None):
		config=copy.copy(self.config)
		return self._get_value(key,config,default)

	def _get_value(self,key,config,default):
		keys=key.split('.',1)
		if len(keys) == 1:
			return config.get(keys[0],default)
		else:
			return self._get_value(keys[1],config.get(keys[0],{}),default)
