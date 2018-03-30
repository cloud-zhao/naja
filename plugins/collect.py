# -*- coding: UTF-8 -*-

import time
import json
import psutil
import os
import sys
import copy
from naja.util import MyTools,SysPs,Properties
from naja.send import SendHttp
from naja.mysql import MysqlDB
from naja.config import RemoteConfig
from naja.plugin import TRun
from naja.plugin import DRun
from collections import namedtuple

Host=namedtuple("Host",['hostId','hostName','user','ip','mem','cpu','net','disk','proc','role'])
class CollectSysMsg(TRun):
	PROJECT_NAME = "naja"
	DEFAULT_CONFIG={
		'send_type':None,
		'send_func':None,
	}
	MYSQL_CONFIG={
		'mysql_host':None,
		'mysql_user':'naja',
		'mysql_db':'naja',
		'mysql_password':None,
		'mysql_port':3306
	}
	SER_CONFIG={
		'ser_host':None,
		'ser_url':None
	}
	REMOTE_CONFIG={
		'local_conf':"%s/s.properties" % (MyTools.get_abs_path(__file__)),
		'local_version': None,
		'remote_server':"http://172.17.124.208:9200/naja/source"
	}

	logger = MyTools.getLogger(__name__+".CollectSysMsg")

	@staticmethod
	def main(configFile):
		proper=Properties(MyTools.get_abs_file(configFile))
		conf=proper.get_value(CollectSysMsg.PROJECT_NAME)
		return CollectSysMsg(**conf)

	def __init__(self,**config):
		#load config
		self.conf=copy.copy(self.DEFAULT_CONFIG)
		self._load_conf(self.conf,config)
		self._load_mysql_conf(config)
		self._load_remote_conf(config)
		self._load_ser_conf(config)

		self.abs_path=MyTools.get_abs_path(__file__)
		self.rc=RemoteConfig(project_name=self.PROJECT_NAME,**self.conf)
		self.mysql=None
		self.sendHttp=None
		self.sys_ps=SysPs()
		self.host_id=MyTools.get_uuid(True)
		self._load_old_info()
		self.info={
				"hostid":self.host_id,
				"hostname":MyTools.get_hostname(),
				"cpu":	{},
				"mem":	{},
				"disk":	{},
				"proc":	{},
				"role":	{},
				"net":	{},
				"user":MyTools.get_user()
			}

	def _load_remote_conf(self,config):
		self._load_conf(self.REMOTE_CONFIG,config)

	def _load_mysql_conf(self,config):
		self._load_conf(self.MYSQL_CONFIG,config)

	def _load_ser_conf(self,config):
		self._load_conf(self.SER_CONFIG,config)

	def _load_conf(self,CONFIG,config):
		for k in CONFIG:
			if k in config:
				self.conf[k]=config[k]
			else:
				self.conf[k]=CONFIG[k]

	def _load_old_info(self):
		old_file=self.abs_path+"/.collectSysMsg.old.json"
		try:
			if os.path.exists(old_file):
				info_str=MyTools.head(old_file)
				self.old_info=json.loads(info_str[0])
			else:
				self.old_info={}
		except:
			self.old_info={}

	def _write_old_info(self):
		old_file=self.abs_path+"/.collectSysMsg.old.json"
		MyTools.write_file(old_file,json.dumps(self.old_info))

	def _now_time(self):
		return int(time.time()*1000)

	def get_sleep(self):
		return 1

	def get_schedule(self):
		return 5

	def role_message(self):
		rc=self.rc
		role={}
		ps=self.sys_ps
		roles=rc.get_config('role')
		r=self._roles(roles)
		for k,v in r.items():
			if ps.get_process(cmd=v):
				role[k]={'status':1}
				self.info['role'][k]=role[k]
		for i in self.info['role'].keys():
			if i not in role.keys():
				self.info['role'][i]['status']=0

	def _roles(self,r,k=None,s={}):
		for i in r.keys():
			p=i if not k else k+"."+i
			if not isinstance(r[i],dict):
				s[p]=r[i]
			else:
				self._roles(r[i],p,s)
		return s

	def _mem(self):
		r_mem={}
		mem=psutil.virtual_memory()
		r_mem['total']=mem.total
		r_mem['used']=mem.used
		r_mem['free']=mem.free
		r_mem['buffer']=mem.buffers if hasattr(mem,'buffers') else 0
		r_mem['cached']=mem.cached if hasattr(mem,'cached') else 0
		r_mem['shared']=mem.shared if hasattr(mem,'shared') else 0
		return r_mem

	def _cpu(self):
		r_cpu={}
		cpu=psutil.cpu_times_percent()
		r_cpu['idle']=cpu.idle
		r_cpu['user']=cpu.user
		r_cpu['system']=cpu.system
		return r_cpu

	def _disk(self):
		r_disk={}
		disk_io=psutil.disk_io_counters(perdisk=True)
		for i in psutil.disk_partitions():
			r_disk[i.mountpoint]={"device":i.device,"fstype":i.fstype}
		for k,v in r_disk.items():
			device=os.path.basename(v['device'])
			u=psutil.disk_usage(k)
			v['total']=u.total
			v['used']=u.used
			v['percent']=u.percent
			if disk_io.has_key(device):
				v['read']=disk_io[device].read_bytes
				v['read_time']=disk_io[device].read_time
				v['write']=disk_io[device].write_bytes
				v['write_time']=disk_io[device].write_time
			else:
				v['read']=0
				v['write']=0
				v['read_time']=1
				v['write_time']=1
		return r_disk

	def _disk_rate(self):
		od=self.old_info.get('disk',{})
		d=self.info['disk']
		rd={}
		for k,v in d.items():
			o_r=od[k]['read'] if od.has_key(k) else v['read']
			o_w=od[k]['write'] if od.has_key(k) else v['write']
			rrate=v['read']-o_r/float(self.get_schedule())
			wrate=v['write']-o_w/float(self.get_schedule())
			rd[k]={'read':rrate,'write':wrate}
		return rd

	def _net(self):
		i_net={}	#ip is key
		r_net={}	#ifName is key
		for i in MyTools.get_netcard():
			i_net[i[1]]=r_net[i[0]]={"ip":i[1],"recv":0,"sent":0,"link":0,"total_link":0}
		try:
			links=psutil.net_connections()
			flow=psutil.net_io_counters(pernic=True)
		except:
			links=[]
			flow={}
		for i in links:
			if i_net.has_key(i.laddr.ip):
				i_net[i.laddr.ip]['link']+=1
		for i in i_net:
			i_net[i]['total_link']=len(links)
		for i in r_net:
			r_net[i]['recv']=flow[i].bytes_recv if flow else 0
			r_net[i]['sent']=flow[i].bytes_sent if flow else 0
		return r_net

	def _net_rate(self):
		o_net=self.old_info.get('net',{})
		net=self.info['net']
		nr={}
		for i in net:
			o_sent=o_net.get(i,{"sent":net[i]['sent']})['sent']
			o_recv=o_net.get(i,{"recv":net[i]['recv']})['recv']
			rsent=(net[i]['sent']-o_sent)/float(self.get_schedule())
			rrecv=(net[i]['recv']-o_recv)/float(self.get_schedule())
			nr[i]={'sent':rsent,'recv':rrecv}
		return nr

	def _proc(self):
		r_proc={}
		r_proc['total']=len(psutil.pids())
		return r_proc

	def sys_message(self):
		self.info['cpu']=self._cpu()
		self.info['mem']=self._mem()
		self.info['net']=self._net()
		self.info['proc']=self._proc()	#proc 未写入表
		self.info['disk']=self._disk()


	def run(self):
		rc=self.rc
		rc.update_config()
		conf=rc.get_config(self.PROJECT_NAME,{})
		for i in self.REMOTE_CONFIG:
			if conf.has_key(i) and conf[i] != self.conf[i]:
				self.rc=RemoteConfig(project_name=self.PROJECT_NAME,**conf)
				break
		for i in self.MYSQL_CONFIG:
			if conf.has_key(i) and conf[i] != self.conf[i] and self.mysql:
				self.mysql.close()
				self.mysql=None
				break
		self._load_conf(self.conf,conf)
		self.sys_message()
		self.role_message()
		self.send()

	def send(self):
		try:
			t=self.conf['send_type']
			if t == "ser":
				self.send_ser()
			elif t == "mysql":
				self.send_mysql()
			else:
				jinfo=json.dumps(self.info)
				if self.conf['send_func']:
					self.conf['send_func'](jinfo)
				else:
					self._send_func(jinfo)
			self.old_info=copy.copy(self.info)
			self._write_old_info()
		except:
			self.logger.exception("send failed.")

	def _send_func(self,jinfo):
		print jinfo

	def send_ser(self):
		url=self.conf['ser_url']
		host=self.conf['ser_host']
		if not url:
			assert host,"ser_host parameters must be specified"
		if not self.sendHttp:
			self.sendHttp=SendHttp()
		url=url if url else "http://%s/naja/host" %host
		header={'Content-type':'application/json'}
		data=json.dumps(self._create_host())
		try:
			res=self.sendHttp.send_info(url=url,header=header,data=data)
		except:
			self.logger.exception("send http server failed.")
		

	def send_mysql(self):
		h=self.conf['mysql_host']
		p=self.conf['mysql_password']
		assert h,"mysql_host parameters must be specified"
		assert p,"mysql_password parameters must be specified"
		if not self.mysql:
			self.mysql=MysqlDB(host=h,db=self.conf['mysql_db'],user=self.conf['mysql_user'],password=p,port=self.conf['mysql_port'])
		mysql=self.mysql
		oi=self.old_info
		ni=self.info
		host_id=self.host_id
		sqls=[]
		sqls.append(self._host_sql())
		sqls.append(self._ip_sql())
		sqls.append(self._role_sql())
		sqls.append(self._cpu_sql())
		sqls.append(self._mem_sql())
		sqls.append(self._disk_sql())
		sqls.append(self._net_sql())
		#for i in sqls:
		#	print i
		mysql.multiple_write(";".join(sqls))

	def _role_sql(self):
		hid=self.host_id
		o_role=self.old_info.get('role',{})
		role=self.info['role']
		timestamp=self._now_time()
		nr=[i for i in role if i not in o_role]
		ur=[i for i in role if i in o_role]
		if nr:
			role_sql='insert into roles (host_id,host_role,timestamp) values '
			role_sql+=",".join(['("%s","%s",%d)' % (hid,r,timestamp) for r in nr])
		else:
			role_sql=''
		if o_role:
			urole_sql='update roles set timestamp=%d where host_id="%s" and host_role="%s"'
			urole_sql=';'.join([urole_sql %(timestamp,hid,i) for i in ur if role[i]['status'] == 1])
		else:
			urole_sql=''
		return role_sql+";"+urole_sql

	def _ip_sql(self):
		hid=self.host_id
		o_net=self.old_info.get("net",{})
		net=self.info['net']
		timestamp=self._now_time()
		if not net:
			return ''
		nc=[(i,net[i]['ip']) for i in net if i not in o_net]
		unc=[(i,net[i]['ip']) for i in net if i in o_net and net[i]['ip'] != o_net[i]['ip']]
		if nc:
			ip_sql='insert into ips values '
			ip_sql+=",".join(['("%s","%s","%s",%d)' % (hid,n[0],n[1],timestamp) for n in nc])
		else:
			ip_sql=''
		if unc:
			uip_sql='update ips set timestamp=%d,host_ip="%s" where host_ifname="%s" and host_id="%s"'
			uip_sql=';'.join([uip_sql % (timestamp,i[1],i[0],hid) for i in unc])
		else:
			uip_sql=''
		return ip_sql+";"+uip_sql
		

	def _host_sql(self):
		hid=self.host_id
		o_info=self.old_info
		info=self.info
		timestamp=self._now_time()
		if o_info:
			host_sql='update hosts set timestamp=%d%s where host_id="%s"'
			if o_info['hostname'] != info['hostname']:
				host_sql=host_sql %(timestamp,',host_name="%s"' % info['hostname'],hid)
			else:
				host_sql=host_sql %(timestamp,'',hid)
		else:
			host_sql='insert into hosts values ("%s","%s",%d)' %(hid,info['hostname'],timestamp)

		return host_sql

	def _cpu_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		cpu=self.info['cpu']
		cpu_sql='insert into cpu values ("%s",%0.2f,%0.2f,%0.2f,%d)'
		return cpu_sql % (hid,cpu['user'],cpu['system'],cpu['idle'],timestamp)

	def _mem_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		mem=self.info['mem']
		mem_sql='insert into mem values ("%s",%d,%d,%d,%d,%d,%d,%d)'
		return mem_sql % (hid,mem['total'],mem['used'],mem['free'],mem['shared'],mem['buffer'],mem['cached'],timestamp)

	def _disk_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		d=self.info['disk']
		disk_sql='insert into disk values '
		value='("%s","%s","%s","%s",%d,%d,%0.2f,%0.2f,%d)'
		values=[]
		disk_rate=self._disk_rate()
		for k,v in d.items():
			rrate=disk_rate[k]['read']
			wrate=disk_rate[k]['write']
			values.append(value % (hid,k,v['device'],v['fstype'],v['total'],v['used'],rrate,wrate,timestamp))
		disk_sql+=','.join(values)
		return disk_sql

	def _net_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		n=self.info['net']
		net_sql='insert into net_io values '
		value='("%s","%s",%0.2f,%0.2f,%d,%d,%d)'
		values=[]
		net_rate=self._net_rate()
		for k,v in n.items():
			rrate=net_rate[k]['recv']
			srate=net_rate[k]['sent']
			values.append(value %(hid,k,srate,rrate,v['link'],v['total_link'],timestamp))
		net_sql+=','.join(values)
		return net_sql
	

	def _create_ip(self):
		i=self.info['net']
		hid=self.info['hostid']
		ips=[]
		net_io=[]
		now_time=self._now_time()
		rni=self._net_rate()
		for k in i:
			ip = {'id':hid,'ifName':k,'ip':i[k]['ip'],'timestamp':now_time}
			ips.append(ip)
			ni={"id":hid,"ifName":k,"sent":rni[k]['sent'],"recv":rni[k]['recv'],"link":i[k]['link'],"totalLink":i[k]['total_link']}
			ni['timestamp']=now_time
			net_io.append(ni)
		return (ips,net_io)

	def _create_role(self):
		r=self.info['role']
		hid=self.info['hostid']
		roles=[]
		nt=self._now_time()
		for i in r:
			if r[i]['status'] == 1:
				role = {'id':hid,'role':i,'table':None,'timestamp':nt}
				roles.append(role)
		return roles

	def _create_cpu(self):
		c=self.info['cpu']
		hid=self.info['hostid']
		cpu={'id':hid,'user':c['user'],'sys':c['system'],'idle':c['idle'],'timestamp':self._now_time()}
		return cpu

	def _create_memory(self):
		m=self.info['mem']
		hid=self.info['hostid']
		mem={'id':hid,'total':m['total'],
			'used':m['used'],'free':m['free'],
			'shared':m['shared'],'buffer':m['buffer'],
			'cached':m['cached'],'timestamp':self._now_time()}
		return mem

	def _create_disk(self):
		d=self.info['disk']
		hid=self.info['hostid']
		nt=self._now_time()
		disks=[]
		rd=self._disk_rate()
		for i in d:
			disk={'id':hid,'mount':i,'device':d[i]['device'],'fsType':d[i]['fstype'],
				'total':d[i]['total'],'used':d[i]['used'],
				'ioRead':rd[i]['read'],'ioWrite':rd[i]['write'],'timestamp':nt}

			disks.append(disk)
		return disks

	def _create_host(self):
		hid=self.info['hostid']
		user=self.info['user']
		hname=self.info['hostname']
		(ip,net)=self._create_ip()
		mem=self._create_memory()
		cpu=self._create_cpu()
		disk=self._create_disk()
		role=self._create_role()
		proc=self.info['proc']

		return {'hostId':hid,'hostName':hname,'user':user,'ip':ip,'mem':mem,'cpu':cpu,'net':net,'disk':disk,'proc':proc,'role':role}


#表示一个yarn的container
Container=namedtuple("Container",["hostId","appId","containerId"])
#表示一台主机上所有非appMaster类型的container
HostContainer=namedtuple("HostContainer",["hostId","containers"])

#表示一个spark app 其中containers表示这个app所有的container
SparkApp=namedtuple("SparkApp",["hostId","appId","userClass","appName","containers"])
#表示一个主机上所有的spark app drive
HostApp=namedtuple("HostApp",["hostId","apps"])

#表示一个主机上所有的任务
HostJob=namedtuple("HostJob",["hostId","hostApp","hostContainer"])
class CollectYarnAppMsg():
	"""
	Collect yarn application message
	Parameter:
		keyword = {
			"containerRole":"cmdlineKeyword"
		}
		func = {
			"containerRole":Function(containerRole,cmdlineKeyword) return List(dict(id:T),dict(id:List[R]))
		}
	"""
	DEFAULT={
		"keyword":{},
		"func":{},
	}
	KEYWORD={
		"drive":"org.apache.spark.deploy.yarn.ApplicationMaster",
		"executor":"org.apache.spark.executor.CoarseGrainedExecutorBackend"
	}
	logger = MyTools.getLogger(__name__+".CollectYarnAppMsg")

	def __init__(self,**config):
		self.conf = MyTools.load_config(self.DEFAULT,config)
		self.ps = SysPs()
		self.conf["keyword"].update(self.KEYWORD)
		self.keyword = self.conf["keyword"]
		self.func = self.conf['func']
		self.host_id = MyTools.get_uuid(True)
	
	"""
	return HostJob(hostId="",hostApp=HostApp,hostContainer=HostContainer)
	{	"hostId":"",
		"hostApp":{	"hostId":"",
					"apps":[{
							"hostId":"xx",
							"appId":"xx",
							"userClass":"xx",
							"appName":"xx",
							"containers":[Container._asdict,...]},
							{...}
					]
		},
		"hostContainer":{"hostId":"xx",
					"containers":[{
							"hostId":"xx",
							"appId":"xx",
							"containerId":"xx"},
							{...}
					]
		}
	}
	"""
	def get_app(self):
		res=self._get_app_all()
		hostApp=HostApp(self.host_id,res[0])
		hostContainer=HostContainer(self.host_id,res[1])
		return MyTools.namedtuple_dict(HostJob(self.host_id,hostApp,hostContainer))

	def _get_app_all(self):
		apps=[]
		containers=[]
		res=self._get_app()
		apps.extend(res[0])
		containers.extend(res[1])
		for k,v in self.keyword.items():
			if k not in self.KEYWORD.keys():
				res=self._get_self_app(k,v)
				apps.extend(res[0])
				containers.extend(res[1])
		return [apps,containers]

	def _get_self_app(self,app_role,cmd):
		func=self.func[app_role]
		res=[]
		if callable(func):
			try:
				res=func(app_role,cmd)
			except:
				self.logger.warning("self get_app failed. %s : %s" %(app_role,cmd))
		if isinstance(res,list) and res and len(res) == 2:
			if isinstance(res[0],dict) and isinstance(res[1],dict):
					return self._set_app_container(res[0],res[1])
		return [[],[]]

	def _get_app(self):
		dl=self._get_drive()
		el=self._get_executor()
		return self._set_app_container(dl,el)

	def _set_app_container(self,drive_list,executor_list):
		for appid,app in drive_list.items():
			if executor_list.has_key(appid):
				app.containers.extend(executor_list[appid])
				del executor_list[appid]
		el_values=[]
		for i in executor_list.values():
			el_values.extend(i)
		return [drive_list.values(),el_values]
		
	def _get_drive(self):
		app_list={}
		proc=self.ps.get_process(cmd=self.keyword['drive'])
		for pid,cmdline in proc.items():
			if cmdline[0] == "/bin/bash" and len(cmdline) == 3:
				continue
			appid=self._get_appid(cmdline)
			appmsg=self._get_drive_msg(cmdline)
			if appid and len(appid) == 2:
				container=Container(self.host_id,appid[0],appid[1])
				if appmsg and len(appmsg) == 2:
					app_list[appid[0]]=SparkApp(self.host_id,appid[0],appmsg[0],appmsg[1],[container])
		return app_list

	def _get_executor(self):
		app_list={}
		proc=self.ps.get_process(cmd=self.keyword['executor'])
		for pid,cmdline in proc.items():
			if cmdline[0] == "/bin/bash" and len(cmdline) == 3:
				continue
			appid=self._get_appid(cmdline)
			if appid and len(appid) == 2:
				container=Container(self.host_id,appid[0],appid[1])
				if app_list.has_key(appid[0]):
					app_list[appid[0]].append(container)
				else:
					app_list[appid[0]]=[container]
		return app_list

	def _get_drive_msg(self,cmdline):
		param=[]
		for i in range(len(cmdline)):
			if cmdline[i] == "--class":
				param.append(cmdline[i+1])
			elif cmdline[i] == "--properties-file":
				param.append(cmdline[i+1])
		try:
			p=Properties(param[1])
			app_name=p.get_value("spark.app.name")
		except:
			app_name=None
		if len(param) == 2:
			return [param[0],app_name]
		else:
			return []

	def _get_appid(self,cmdline):
		cmd_keyword="-Djava.io.tmpdir"
		for i in cmdline:
			if cmd_keyword in i:
				v=i.split("/")
				return v[-3:-1]
		return []
