import os
import re
import pwd
import sys
import copy
import time
import logging
import threading
from Queue import Empty,Full
from multiprocessing import Process,Queue
from naja.util import Properties,MyTools
from naja.send import SendHttp
from collections import namedtuple


class MyPlugin(object):
	logger = MyTools.getLogger(__name__+".MyPlugin")
	def run(self):
		pass
	@staticmethod
	def main(configFile):
		return None
class TRun(MyPlugin):
	def get_sleep(self):
		return 0
	def get_schedule(self):
		return 0
class DRun(MyPlugin):
	def get_daemon_level(self):
		return 0

class DynamicImport(TRun):
	def __init__(self):
		self.showPlugin=ShowPlugin()
	def get_sleep(self):
		return 5
	def get_schedule(self):
		return 30
	def run(self):
		self.showPlugin.show_plugin()
		self.logger.info("showPlugin.show_plugin()")

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
		self.conf = MyTools.load_config(self.DEFAULT_CONFIG,config)
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
				else:
					reload(self.alreadyImportM[packageName])
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
			else:
				reload(self.alreadyImportP[p])
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
	
SchedulerFunc=namedtuple("SchedulerFunc",["name","obj"])
class ProcessScheduler(Process):
	"""
	Process scheduler
	"""
	logger = MyTools.getLogger(__name__+".ProcessScheduler")

	DEFAULT = {
		"maxSize":8,
		"queue":None,
	}

	def __init__(self,**config):
		Process.__init__(self)
		self.conf = MyTools.load_config(self.DEFAULT,config)
		self.queue = self.conf['queue']
		self.size = 0
		self.threadList = []

	def _get_queue(self,queue,block=True,timeout=10):
		f=None
		try:
			f=queue.get(block=block,timeout=timeout)
		except Empty:
			self.logger.warning("get queue timeout %d" %timeout)
		except Exception,e:
			self.logger.error(e,exc_info=1)
		return f

	def _put_queue(self,cxt,queue,block=True,timeout=5):
		res=False
		try:
			queue.put(cxt,block=block,timeout=timeout)
			res=True
		except Full:
			self.logger.warning("put queue timeout %d" %timeout)
		except Exception,e:
			self.logger.error(e,exc_info=1)
		return res

	def _size(self):
		removeList = []
		for i in self.threadList:
			if not i.is_alive():
				self.size -= 1
				removeList.append(i)
		for i in removeList:
			self.threadList.remove(i)

	
	def runFunc(self):
		startTime = int(time.time()*1000)
		while 1:
			try:
				i = self._get_queue(self.queue) if self.size < self.conf['maxSize'] else None
				if i:
					f = self.create_func(i)
					p = self._run(f)
					self.size += 1
					self.threadList.append(p)
				else:
					self._size()
			except Exception,e:
				self.logger.error(e,exc_info=1)

	def run(self):
		self.runFunc()

	def _run(self,func):
		p = threading.Thread(target=func)
		p.setDaemon(True)
		p.start()
		return p

	@staticmethod
	def create_func(sf):
		def _func_():
			time.sleep(sf.obj.get_sleep())
			while 1:
				try:
					sf.obj.run()
					if sf.obj.get_schedule() > 0:
						time.sleep(sf.obj.get_schedule())
					else:
						break
				except Exception,e:
					ProcessScheduler.logger.warning("run %s failed. " %sf.name)
					ProcessScheduler.logger.warning(e,exc_info=1)
					time.sleep(40)
		return _func_

class SchedulerFork(Process):
	"""
	Scheduler fork
	"""
	logger = MyTools.getLogger(__name__+".SchedulerFork")

	def __init__(self,**func):
		Process.__init__(self)
		self.func=func
		self.thread=[]

	def run(self):
		for i in self.func:
			self.logger.info("run %s" % i)
			p=threading.Thread(target=self.func[i])
			self.thread.append(p)
		for i in self.thread:
			i.setDaemon(True)
			i.start()
		for i in self.thread:
			i.join()


class RunPlugin(object):
	"""
	Run plugin
	"""

	DEFAULT_CONFIG = {
			"processNumber":8,
			"configFile":None,
			"configPrefix":"config.file"
	}

	logger = MyTools.getLogger(__name__+".RunPlugin")

	def __init__(self,**config):
		self.conf = copy.copy(self.DEFAULT_CONFIG)
		for i in self.conf:
			if i in config:
				self.conf[i]=config[i]
		self.processNumber=self.conf['processNumber']
		assert self.conf['configFile'],"configFile parameters must be set"
		self.proper = Properties(self.conf['configFile'])
		self.showPlugin=DynamicImport()
		self.alreadyF = {}
		self.alreadyD = {}
		self.queue = Queue(self.processNumber)
		self.procScheduler = None

	def _get_T(self):
		tf={}
		sp = self.showPlugin.showPlugin
		spt=sp.get_t()
		for i in spt:
			if i not in self.alreadyF:
				self.alreadyF[i]=spt[i]
				f=spt[i].main(self.proper.get_value("%s.%s" %(self.conf['configPrefix'],i),""))
				if f:
					tf[i]=f
		return tf
	def _get_D(self):
		tf = {}
		sp = self.showPlugin.showPlugin
		spd = sp.get_d()
		for i in spd:
			if i not in self.alreadyD:
				self.alreadyD[i]=spd[i]
				f=spd[i].main(self.proper.get_value("%s.%s" %(self.conf['configPrefix'],i),""))
				if f:
					tf[i]=f
		return tf

	def _run_T(self,tf):
		self._create_scheduler()
		for i in tf:
			sff = SchedulerFunc(i,tf[i])
			self.procScheduler._put_queue(sff,self.queue,block=False)
			self.logger.info(str(tf[i].run))

	def _run_D(self,df):
		dp = []
		for i in df:
			def _r_d_():
				try:
					df[i].run()
				except Exception,e:
					self.logger.error(e,exc_info=1)
			if i.get_daemon_level() == 0:
				dThread = threading.Thread(target=_r_d)
				dThread.setDaemon(True)
			else:
				dThread = Process(target=_r_d)
				dThread.daemon=True
			dp.append(dThread)
		return dp

	def _run_dynamic(self):
		sp = self.showPlugin
		dynamicFunc = SchedulerFunc("DynamicImport",sp)
		#self.queue.put(dynamicFunc)
		dynamicRun = ProcessScheduler.create_func(dynamicFunc)
		dynamicThread = threading.Thread(target=dynamicRun)
		dynamicThread.setDaemon(True)
		dynamicThread.start()
		return dynamicThread
		
	def _load_TD(self):
		works = []
		tf = self._get_T()
		self._run_T(tf)
		df = self._get_D()
		_dwork = self._run_D(df)
		works.extend(_dwork)
		for i in works:
			i.start()
			self.logger.info("start works %s" %str(i))

	def _create_scheduler(self):
		if not self.procScheduler:
			self.procScheduler = ProcessScheduler(queue=self.queue,maxSize=self.processNumber)
			self.procScheduler.daemon = True

	def run(self):
		self._create_scheduler()
		self.procScheduler.start()
		self._run_dynamic()
		while 1:
			try:
				self._load_TD()
				time.sleep(5)
			except KeyboardInterrupt:
				break

