import os
import sys
import time
import json
import Queue
from naja.plugin import DRun,TRun
from naja.util import MyTools
from naja.send import SendHttp
from collections import namedtuple
from threading import Thread


Job=namedtuple("Job",["id","jobType","packageName","script"])
SubmitJob=namedtuple("SubmitJob",["deployJob","hosts"])
GetHostReadyJob=namedtuple("GetHostReadyJob",["host"])
CompleteJob=namedtuple("CompleteJob",["id","host","fetchTime","completeTime","result"])
JobResult=namedtuple("JobResult",["stdout","stderr","exitCode"])
NajaBody=namedtuple("NajaBody",["code","msg","data"])

class DynamicDeploy(DRun):
	logger = MyTools.getLogger(__name__+".DynamicDeploy")
	PROJECT_NAME = "naja"
	DEFAULT_CONFIG = {
		"local_stored":None,
		"remote_server":None,
		"remote_url":"naja/deploy"
	}
	
	@staticmethod
	def main(remoteConfig):
		config=remoteConfig.get_config(DynamicDeploy.PROJECT_NAME)
		return DynamicDeploy(**config)
	
	def __init__(self,**config):
		self.conf = MyTools.load_config(self.DEFAULT_CONFIG,config)
		self.host_id = MyTools.get_host_id()
		self.send_http = SendHttp()
		self.jobs = {}
		self.run_queue = Queue.Queue()
		self.proc_queue = Queue.Queue(4)
		self.result_queue = Queue.Queue()
		self.run_thread = RunDeployJob(self,self.run_queue,self.proc_queue)
		self.result_thread = FetchJobResult(self.proc_queue,self.result_queue)

	def run(self):
		self.logger.info("run DynamicDeploy from deploy.py,config: %s" %self.cf)
		self.run_thread.setDaemon(True)
		self.result_thread.setDaemon(True)
		self.run_thread.start()
		self.result_thread.start()
		while 1:
			try:
				self.fetch_host_ready_job()
			except:
				self.logger.exception("fetch host ready job failed.")
			self.fetch_job_res()

	def fetch_job_res(self):
		while 1:
			try:
				(job_id,res) = self.result_queue.get(block=False,timeout=5)
				self.send_complete_job(job_id,res)
				del self.jobs[job_id]
			except Queue.Empty:
				break
			except Exception,e:
				self.logger.error("fetch job result failed. %s" %e.message)

	def fetch_host_ready_job(self):
		host_id = self.host_id
		get_job = GetHostReadyJob(host_id)
		url = "%s/%s/ready?host=%s" % (self.conf["remote_server"],self.conf['remote_url'],get_job.host)
		method = "GET"
		res = self.send_http.send_info(url=url,method=method)
		body = create_body(res)
		data_list = json.loads(body.data) if body.data else []
		jobs = [Job(**i) for i in data_list]
		for job in jobs:
			if job.id not in self.jobs:
				self.jobs[job.id]=(int(time.time()*1000),job)
				self.run_queue.put(job)

	def send_complete_job(self,job_id,res):
		fetch_time = self.jobs[job_id][0]
		cjob = CompleteJob(job_id,self.host_id,fetch_time,int(time.time()*1000),res)
		header = {'Content-type':'application/json'}
		data = json.dumps(MyTools.namedtuple_dict(cjob))
		url = "%s/%s/complete" %(self.conf['remote_server'],self.conf['remote_url'])
		res = self.send_http.send_info(url=url,header=header,data=data)
		body = create_body(res)
		return body

	def get_package(self,job):
		remote_file = "%s/naja/source/%s" %(self.conf['remote_server'],job.packageName)
		local_file = "%s/%s" %(self.conf['local_stored'],job.packageName)
		if self.send_http.get_file(remote_file,local_file) and MyTools.untar(local_file,self.conf['local_stored']):
			return "%s/%s" %(self.conf['local_stored'],job.script)
		return None

	def create_body(self,res):
		rd = NajaBody(-9,"except",None)
		if res and hasattr(res,"read"):
			try:
				data=json.loads(res.read())
				rd = NajaBody(**data)
			except:
				self.logger.exception("create ResponseData failed.")
		return rd


class RunDeployJob(Thread):
	def __init__(self,dynamic_deploy,input_queue,output_queue):
		self.iq = input_queue
		self.oq = output_queue
		self.dd = dynamic_deploy

	def run_job(self,job):
		if job.jobType == "deploy":
			run_script = self.dd.get_package(job)
			if run_script:
				proc = subprocess.Popen(run_script,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd="/")
				self.oq.put((job.id,proc),block=True)

	def get_job(self):
		while 1:
			job = self.iq.get()
			self.run_job(job)

	def run(self):
		self.get_job()


class FetchJobResult(Thread):
	def __init__(self,iq,oq):
		self.iq = iq
		self.oq = oq

	def complete_job(self):
		while 1:
			(job_id,proc)=self.iq.get()
			res = proc.communicate()
			job_result=JobResult(res[0],res[1],proc.poll())
			self.oq.put((job_id,job_result),block=True)

	def run(self):
		self.complete_job()


class DeployCode(TRun):
	logger = MyTools.getLogger(__name__+".DeployCode")
	PROJECT_NAME = "naja"
	DEFAULT_CONFIG = {
		"local_package":MyTools.get_abs_path(__file__),
		"remote_file":"naja/source/codes/code_list.json",
		"remote_server":None,
	}

	@staticmethod
	def main(remoteConfig):
		config = remoteConfig.get_config(DeployCode.PROJECT_NAME)
		return DeployCode(**config)

	def __init__(self,**config):
		self.conf = MyTools.load_config(self.DEFAULT_CONFIG,config)
		self.send_http = SendHttp()

	def _get_code_list(self):
		"""
		code_path: http://127.0.0.1:8920/naja/source/codes/code_list.json
		code_list.json: ["test.py"]
		"""

		code_path = "%s/%s" % (self.conf['remote_server'],self.conf['remote_file'])
		code_local_path = "%s/%s" %(MyTools.get_abs_path(__file__),"code_local.json")
		try:
			code_str = self.send_http.get_chunk(code_path)
			code_list = json.loads(code_str)
		except Exception,e:
			self.logger.warning("get code list failed. %s" % e.message)
			code_list = []

		if os.path.exists(code_local_path):
			code_local_list = self.send_http.get_local_info(code_local_path)
		else:
			code_local_list = []
		code1=set(code_list)
		code2=set(code_local_list)
		ready_code_list = list(code1-code2)
		self.sh.write_local_info(code_local_path,json.dumps(list(code1|code2)))
		return ready_code_list

	def get_code(self):
		remote_code_path = "%s/%s" %(self.conf['remote_server'],"naja/source/codes")
		for i in self._get_code_list():
			self.send_http.get_file("%s/%s" %(remote_code_path,i),"%s/%s" %(self.conf['local_package'],i))

	def run(self):
		self.get_code()




