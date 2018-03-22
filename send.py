import os
import copy
import json
import urllib
import urllib2
from kafka import KafkaProducer
from naja.util import MyTools



class SendInfoInterface(object):
	"""
	first send info hostid set NULL
	"""

	def get_local_chunk(self,rfile):
		if not os.path.isfile(rfile):
			return ""
		try:
			with open(rfile,"r") as f:
				buf=f.read()
		except:
			buf=""
		return buf

	def get_local_info(self, rfile):
		buf=self.get_local_chunk(rfile)
		return json.loads(buf)

	def write_local_chunk(self, wfile, info):
		try:
			with open(wfile,"w") as fh:
				fh.write(info)
				return True
		except:
			return False

	def write_local_info(self,wfile,info):
		self.write_local_chunk(wfile,json.dumps(info))

	def send_info(self, jsonDict):
		pass


class SendHttp(SendInfoInterface):
	DEFAULT_CONFIG={
		'header':{},
		'method':"POST",
		'data':{},
		'url':None,
	}
	logger = MyTools.getLogger(__name__+".SendHttp")

	def send_info(self,**config):
		conf=MyTools.load_config(self.DEFAULT_CONFIG,config)
		assert conf['url'],"url not null"

		res=None
		req=urllib2.Request(url=conf['url'])
		if conf['data']:
			#dataEncode=urllib.urlencode(conf['data'])
			#req.add_data(dataEncode)
			req.add_data(conf['data'])
		req.get_method = lambda: conf['method']
		for headerKey in conf['header']:
			req.add_header(headerKey,conf['header'][headerKey])
		try:
			res=urllib2.urlopen(req)
		except urllib2.HTTPError,e:
			self.logger.error("send request %s failed. Code: %d Msg: %s" %(conf['url'],e.getcode(),e.message))
		except urllib2.URLError,e:
			self.logger.error("url error. "+e.reason)
		except:
			self.logger.error("unknown error.")
		return res

	def get_chunk(self,url):
		res=self.send_info(url=url, method="GET")
		buf=None
		if res:
			buf=res.read()
		return buf

	def get_file(self, url, localfile):
		res=self.send_info(url=url, method="GET")
		fh=None
		try:
			if res:
				with open(localfile,"wb") as fh:
					while True:
						buf=res.read(8192)
						if not buf:
							break
						fh.write(buf)
			else:
				return False
			return True
		except:
			return False
			


class SendKafka(SendInfoInterface):
	"""
		send kafka message
	"""
	logger = MyTools.getLogger(__name__+".SendKafka")

	def __init__(self,server):
		self.servers=server.split(",")
		assert self.servers,"server not null"
		self.producer=KafkaProducer(bootstrap_servers=self.servers)

	def send_info(self,topic,msg={}):
		for key in msg:
			self.producer.send(topic,key=key,value=msg[key])
		self.producer.flush()

