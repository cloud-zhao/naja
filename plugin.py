import os
import re
import pwd
import sys
import copy
import time
import logging
import threading
from multiprocessing import Process
from naja.util import Properties
from naja.send import SendHttp


class MyPlugin(object):
	def run(self):
		pass
class TRun(MyPlugin):
	def get_sleep(self):
		return 0
	def get_schedule(self):
		return 0
class DRun(MyPlugin):
	def get_deamon(self):
		return False

class DynamicImport(TRun):
	def __init__(self):
		self.showPlugin=ShowPlugin()
	def get_sleep(self):
		return 10
	def get_schedule(self):
		return 60
	def run(self):
		self.showPlugin.show_plugin()

class ShowPlugin(object):
	DEFAULT_CONFIG={
		'plugin_package':['naja.plugins'],
		'plugin_path':[],
	}
	alreadyImportT={}
	alreadyImportD={}
	alreadyImportM={}
	alreadyImportP={}

	def __init__(self,**config):
		self.conf=copy.copy(self.DEFAULT_CONFIG)
		for key in self.conf:
			if key in config:
				self.conf[key]=config[key]
		self._dynamic_class()

	def show_plugin(self):
		self._dynamic_import()
		self._dynamic_class()

	def get_d(self):
		return self.alreadyImportD
	def get_t(self):
		return self.alreadyImportT

	def _dynamic_class(self):
		for ict in TRun.__subclasses__():
			if not self.alreadyImportT.has_key(ict.__name__):
				self.alreadyImportT[ict.__name__]=ict
		for icd in DRun.__subclasses__():
			if not self.alreadyImportD.has_key(ict.__name__):
				self.alreadyImportD[icd.__name__]=icd

	def _dynamic_import(self):
		ms=self._dynamic_search_modules()
		for package,modules in ms['packages'].items():
			for module in modules:
				packageName="%s.%s" %(package.replace("/","."),module[:-3])
				if not self.alreadyImportM.has_key(packageName):
					self.alreadyImportM[packageName]=__import__(packageName,globals(),locals(),[module[:-3]])
		for path,modules in ms['paths'].items():
			for module in modules:
				packageName="__paths.%s" %(module[:-3])
				if not self.alreadyImportM.has_key(packageName):
					if path not in sys.path:
						sys.path.append(path)
					self.alreadyImportM[packageName]=__import__(module[:-3])


	def _dynamic_search_modules(self):
		res={}
		packages=res['packages']={}
		paths=res['paths']={}

		for p in self.conf['plugin_package']:
			if p not in self.alreadyImportP:
				self.alreadyImportP[p]=__import__(p)
		for p,c in self.alreadyImportP.items():
			ms=self._search_can_modules(os.path.dirname(c.__file__))
			for path,mf in ms.items():
				if "__init__.py" in mf:
					mf.remove("__init__.py")
					f=path.find(p.replace(".","/"))
					if f > -1:
						packages[path[f:]]=mf
		for p in self.conf['plugin_path']:
			ms=self._search_can_modules(p)
			for path,mf in ms.items():
				if "__init__.py" not in mf:
					paths[path]=mf
		return res

	def _search_can_modules(self,path):
		res={}
		if not os.path.isdir(path):
				return res
		for i,d,f in os.walk(path):
			tmp=[]
			for pf in f:
				if re.match(r'.+\.py$',pf):
					tmp.append(pf)
			if tmp:
				res[i]=tmp
		return res
	

class RunPlugin(object):
	def __init__(self,processNumber=8):
		self.processNumber=processNumber
		self.process=[]
		self.showPlugin=ShowPlugin()

	def _get_T(self):
		return self.showPlugin.get_t()
	def _get_D(self):
		return self.showPlugin.get_d()

	def _run_T(self,t):
		try:
			time.sleep(t.get_sleep())
			while 1:
				t.run()
				time.sleep(t.get_schedule())
		except Exception,e:
			print e

	def _run_D(self,d):
		try:
			while 1:
				d.run()
		except Exception,e:
			pass

	def _work(self,r):
		p=Process(target=r)
		self.process.append(p)
		p.start()
		p.join()

	def _schedule(self):
		pass
