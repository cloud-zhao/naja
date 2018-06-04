from naja.plugin import TRun
from naja.util import MyTools


#class TRun(MyPlugin):
#	def get_sleep(self):
#		return 0
#	def get_schedule(self):
#		return 0


#class MyT1(TRun):
#	logger = MyTools.getLogger(__name__+".MyT1")
#	def __init__(self,config):
#		self.cf = config
#	def get_sleep(self):
#		return 10
#	def get_schedule(self):
#		return 5
#	def run(self):
#		self.logger.info("run MyT1 from test.py,config: %s" %self.cf)

#	@staticmethod
#	def main(configFile):
#		return MyT1(configFile)

#class MyT2(TRun):
#	logger = MyTools.getLogger(__name__+".MyT2")
#	def __init__(self,config):
#		self.cf = config
#	def get_sleep(self):
#		return 3
#	def get_schedule(self):
#		return 15
#	def run(self):
#		self.logger.info("run MyT2 from test.py,config: %s" %self.cf)

#	@staticmethod
#	def main(configFile):
#		return MyT2(configFile)


#class MyTa(TRun):
#    logger = MyTools.getLogger(__name__+".MyTa")
#    def __init__(self,config):
#        self.cf = config
#    def get_sleep(self):
#        return 3
#    def get_schedule(self):
#        return 4
#    def run(self):
#        self.logger.info("run MyTa from test.py,config: %s" %self.cf)

#    @staticmethod
#    def main(configFile):
#        return MyTa(configFile)
