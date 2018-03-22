import copy
import json
from naja.util import Properties,MyTools
from naja.send import SendHttp


class MyConfig(object):
	base=MyTools.get_abs_path(__file__)
	selfName="naja"
	configFile="%s/%s.properties" % (base,selfName)


class RemoteConfig(MyConfig):
	DEFAULT_CONFIG={
		'local_conf': None,
		'local_version': None,
		'remote_conf': None,
		'remote_version': None,
		'check_version': True,
		'project_name': "naja",
		'remote_server': "http://172.17.124.208:9200/naja/source",
	}
	logger=MyTools.getLogger(__name__+".RemoteConfig")

	def __init__(self,**config):
		self.conf=MyTools.load_config(self.DEFAULT_CONFIG,config)
		assert self.conf['local_conf'],"parameter local_conf not setup"

		self.sh=SendHttp()
		self.localFile=self.conf['local_conf']
		self._abs_conf()
		basename=MyTools.basename(self.localFile,sp='.')
		self.conf['remote_conf']="%s/%s" %(self.conf['remote_server'],self.conf['remote_conf']) if self.conf['remote_conf'] \
					 else "%s/%s/%s" %(self.conf['remote_server'],self.conf['project_name'],MyTools.basename(self.localFile))
		self.conf['remote_version']="%s/%s" %(self.conf['remote_server'],self.conf['remote_version']) if self.conf['remote_version'] \
					 else "%s/%s/%s.version" %(self.conf['remote_server'],self.conf['project_name'],basename)
		self.conf['local_version']=self.conf['local_version'] if self.conf['local_version'] \
					 else "%s/%s.version" %(MyTools.dirname(self.localFile),basename)
		if self._check_version() or not MyTools.exists(self.localFile):
			self._update_config_file()
		assert MyTools.exists(self.localFile),"%s file not found" %(self.localFile)
		self.proper=Properties(self.localFile)
		self.logger.info("init success.")

	def _abs_conf(self):
		if MyTools.exists(self.localFile):
			self.localFile=MyTools.get_abs_file(self.localFile)
		else:
			dirname=MyTools.dirname(self.localFile)
			if not MyTools.exists(dirname):
				self.logger.warning("The %s where the local_conf is located does not exist" %(dirname))
				self.localFile="%s/%s" %(base,MyTools.basename(self.localFile))
			else:
				self.localFile="%s/%s" %(MyTools.get_abs_file(dirname),MyTools.basename(self.localFile))

	def update_config(self):
		if self._check_version() or not MyTools.exists(self.localFile):
			self._update_config_file()
			self.proper=Properties(self.localFile)

	def _update_config_file(self):
		res=self.sh.get_file(self.conf['remote_conf'],self.localFile)
		if res:
			self.logger.info("update remote conf %s to local config %s success" %(self.conf['remote_conf'],self.localFile))
		else:
			self.logger.warning("update remote conf %s to local config %s failed" %(self.conf['remote_conf'],self.localFile))
		return res

	def _check_version(self):
		if not self.conf['check_version']:
			return self.conf['check_version']
		localVersionFile=self.conf['local_version']
		if MyTools.exists(localVersionFile):
			configVersion=self.sh.get_local_info(localVersionFile)
			localVersion=tuple(configVersion['version'].split('.'))
		else:
			localVersion=('0','0','0')

		try:
			configStr=self.sh.get_chunk(self.conf['remote_version'])
			configVersion=json.loads(configStr)
		except Exception,e:
			self.logger.error("version config json loads failed")
			self.logger.error(e,exc_info=1)
			configVersion={'version':'0.0.0'}
		remoteVersion=tuple(configVersion['version'].split('.'))

		if remoteVersion>localVersion:
			self.sh.write_local_info(localVersionFile,configVersion)
		return remoteVersion>localVersion

	def get_config(self,key,default=None):
		return self.proper.get_value(key,default)


