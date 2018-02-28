import time
import json
import psutil
import os
import copy
from naja.util import MyTools,SysPs
from naja.send import SendHttp
from naja.mysql import MysqlDB
from naja.config import RemoteConfig
from naja.plugin import TRun
from naja.plugin import DRun

class CollectSysMsg(TRun):
	def __init__(self,**config):
		self.conf=config
		self.abs_path=MyTools.get_abs_path(__file__)
		self.config_file=config.get('config_file',"%s/s.properties" % (self.abs_path))
		self.rc=RemoteConfig(local_conf=self.config_file)
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
		return int(time.time())

	def get_sleep(self):
		return 1

	def get_schedule(self):
		return 5

	def role_message(self):
		rc=self.rc
		role={}
		ps=self.sys_ps
		rc.update_config()
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
			r_disk[i.mountpoint]={"disk":i.device,"fstype":i.fstype}
		for k,v in r_disk.items():
			device=os.path.basename(v['disk'])
			u=psutil.disk_usage(k)
			v['total']=u.total
			v['used']=u.used
			v['percent']=u.percent
			if disk_io.has_key(device):
				v['read']=disk_io[device].read_bytes/float(disk_io[device].read_time)
				v['write']=disk_io[device].write_bytes/float(disk_io[device].write_time)
			else:
				v['read']=0.0
				v['write']=0.0
		return r_disk

	def _net(self):
		i_net={}
		r_net={}
		for i in MyTools.get_netcard():
			i_net[i[1]]=r_net[i[0]]={"ip":i[1],"link":0,"total_link":0}
		links=psutil.net_connections()
		for i in links:
			i_net[i]['link']+=1
		for i in i_net:
			i_net[i]['total_link']=len(links)
		return r_net

	def _proc(self):
		r_proc={}
		r_proc['total']=len(psutil.pids())
		return r_proc

	def sys_message(self):
		self.info['cpu']=self._cpu()
		self.info['mem']=self._mem()
		self.info['net']=self._net()
		self.info['proc']=self._proc()
		self.info['disk']=self._disk()


	def run(self):
		self.sys_message()
		self.role_message()
		self.send()

	def send(self):
		if self.conf['send_ser']:
			self.send_ser()
		elif self.conf['send_mysql']:
			self.send_mysql()
		else:
			print(json.dumps(self.info))

	def send_ser(self):
		pass

	def send_mysql(self):
		h=self.conf['mysql_host'] if self.conf.has_key('mysql_host') else None
		d=self.conf['mysql_db'] if self.conf.has_key('mysql_db') else None
		u=self.conf['mysql_user'] if self.conf.has_key('mysql_user') else None
		p=self.conf['mysql_password'] if self.conf.has_key('mysql_password') else None
		assert h,"mysql_host parameters must be specified"
		assert d,"mysql_db parameters must be specified"
		assert u,"mysql_user parameters must be specified"
		assert p,"mysql_password parameters must be specified"
		#mysql=MysqlDB(host=h,db=d,user=u,password=p)
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
		for i in sqls:
			print i
		#mysql.multiple_write(";".join(sqls))
		self.old_info=copy.copy(self.info)

	def _role_sql(self):
		hid=self.host_id
		o_role=self.old_info.get('role',{})
		role=self.info['role']
		timestamp=self._now_time()
		nr=[i for i in role.keys() if i not in o_role.keys()]
		if nr:
			role_sql='insert into roles (host_id,host_role,timestamp) values '
			role_sql+=",".join(['("%s","%s","%d")' % (hid,r,timestamp) for r in nr])
		else:
			role_sql=''
		if o_role:
			urole_sql='update roles set timestamp="%d" where host_id="%s" and host_role="%s"'
			urole_sql=';'.join([urole_sql %(timestamp,hid,i) for i in o_role.keys() if o_role[i]['status'] == 1])
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
		nc=[(i,net[i]['ip']) for i in net.keys() if i not in o_net.keys()]
		unc=[(i,net[i]['ip']) for i in net.keys() if i in o_net.keys() and net[i]['ip'] != o_net[i]['ip']]
		if nc:
			ip_sql='insert into ips values '
			ip_sql+=",".join(['("%s","%s","%s","%d")' % (hid,n[0],n[1],timestamp) for n in nc])
		else:
			ip_sql=''
		if unc:
			uip_sql='update ips set timestamp="%d",host_ip="%s" where host_ifname="%s" and host_id="%s"'
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
			host_sql='update hosts set timestamp="%d"%s where host_id="%s"'
			if o_info['hostname'] != info['hostname']:
				host_sql=host_sql %(timestamp,',host_name="%s"' % info['hostname'],hid)
			else:
				host_sql=host_sql %(timestamp,'',hid)
		else:
			host_sql='insert into hosts values ("%s","%s","%d")' %(hid,info['hostname'],timestamp)

		return host_sql

	def _cpu_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		cpu=self.info['cpu']
		cpu_sql='insert into cpu values ("%s","%0.2f","%0.2f","%0.2f","%d")'
		return cpu_sql % (hid,cpu['user'],cpu['system'],cpu['idle'],timestamp)

	def _mem_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		mem=self.info['mem']
		mem_sql='insert into mem values ("%s","%d","%d","%d","%d","%d","%d","%d")'
		return mem_sql % (hid,mem['total'],mem['used'],mem['free'],mem['shared'],mem['buffer'],mem['cached'],timestamp)

	def _disk_sql(self):
		hid=self.host_id
		timestamp=self._now_time()
		d=self.info['disk']
		disk_sql='insert into disk values '
		value='("%s","%s","%s","%s","%d","%d","%0.2f","%0.2f","%d")'
		values=[value % (hid,k,v['disk'],v['fstype'],v['total'],v['used'],v['read'],v['write'],timestamp) for k,v in d.items()]
		disk_sql+=','.join(values)
		return disk_sql
	

	
