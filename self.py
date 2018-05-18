import time
from naja.config import UpdateCode
from naja.util import MyTools

class ReloadProject():
	"""
	reload project
	"""
	logger = MyTools.getLogger(__name__+".ReloadProject")
	
	DEFAULT={
		"file_list":[],
		"version_file":"%s/naja.version" %MyTools.get_abs_path(__file__)
	}

	def __init__(self,**config):
		self.conf=MyTools.load_config(self.DEFAULT,config)
		self._create_update()

	def _create_update(self):
		fileList=self.conf['file_list']
		self.update=[]
		if not isinstance(fileList,list):
			return
		for i in fileList:
			self.update.append(UpdateCode(local_conf=i,local_version=self.conf['version_file']))

	def _reload(self):
		pass

