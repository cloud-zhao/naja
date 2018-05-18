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
import psutil
import logging
from naja.error import ConfigFileError


class MyTools(object):
	@staticmethod
	def get_abs_path(p):
		return os.path.split(os.path.realpath(p))[0]

	@staticmethod
	def get_abs_file(p):
		return os.path.realpath(p)

	@staticmethod
	def now_time():
		return int(time.time()*1000)

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
	def dirname(pathStr,pwd=False):
		dirname=os.path.dirname(pathStr)
		return dirname

	@staticmethod
	def exists(pathStr):
		return os.path.exists(pathStr)

	@staticmethod
	def basename(pathStr,suffix='',sp=None):
		string=os.path.basename(pathStr)
		if sp:
			return string.split(sp)[0]
		else:
			return string[:len(string)-len(suffix)]

	@staticmethod
	def getLogger(name):
		logging.basicConfig(level=logging.INFO,format='%(asctime)s %(name)s %(lineno)d %(levelname)s %(message)s')
		return logging.getLogger(name)

	@staticmethod
	def load_config(default,config):
		conf = copy.copy(default)
		for i in conf:
			if i in config:
				conf[i]=config[i]
		return conf

	@staticmethod
	def namedtuple_dict(ndict):
		if isinstance(ndict,tuple) and hasattr(ndict,"_asdict"):
			d=dict(ndict._asdict())
			for k,v in d.items():
				d[k]=MyTools.namedtuple_dict(v)
			return d
		elif isinstance(ndict,list):
			l=[]
			for i in ndict:
				l.append(MyTools.namedtuple_dict(i))
			return l
		elif isinstance(ndict,dict):
			sd={}
			for k,v in ndict.items():
				sd[k]=MyTools.namedtuple_dict(v)
			return sd
		else:
			return ndict


class SysPs(object):
	ppath="/proc"
	cmd="cmdline"

	def __init__(self):
		self.ps = False
		if not os.path.isdir(self.ppath):
			self.ps=True
			

	def _get_pid(self):
		command={}
		if self.ps:
			for i in psutil.pids():
				try:
					p=psutil.Process(i)
					command[i]=p.cmdline()
				except:
					pass
			return command
		for i in os.listdir(self.ppath):
			if i.isdigit():
				try:
					fh=open(self.ppath+"/"+i+"/"+self.cmd,"r")
					command[int(i)]=fh.read().split(chr(0))
				except:
					pass
				finally:
					if fh:
						fh.close()
		return command

	def get_process(self,pid=None,cmd=None):
		res={}
		if pid == None and cmd == None:
			return res

		clist=self._get_pid()
		if pid != None and pid in clist:
			return {pid:clist[pid].split(chr(0))}
		elif cmd != None:
			for i in clist:
				conditionList=cmd.split('|')
				conditionNum=0
				for c in conditionList:
					if c in clist[i]:
						conditionNum += 1
				if conditionNum == len(conditionList):
					res[i]=clist[i]
			return res
		else:
			return res

	def all(self):
		return self._get_pid()

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
		if value.find('::') > -1:
			res={}
			for j in value.split(',,'):
				k,v=j.split('::')
				res[k.strip()]=v.strip()
		elif value.find(',,') > -1:
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
