import os
import pwd
import sys
import time
import uuid
import copy
import datetime
import MySQLdb


class MysqlDB(object):
	DEFAULT_CONFIG={
		"host":"",
		"port":3306,
		"db":"naja",
		"user":None,
		"password":None,
	}

	def __init__(self,**config):
		self.conf=copy.copy(self.DEFAULT_CONFIG)
		for i in self.conf:
			if i in config:
				self.conf[i]=config[i]
		self.dbh=self._mysql_connect()
		
	def _mysql_connect(self):
		return MySQLdb.connect(self.conf['host'],self.conf['user'],self.conf['password'],self.conf['db'],port=self.conf['port'])

	def _mysql_exec(self,sql):
		try:
			cur=self.dbh.cursor()
			num=cur.execute(sql)
		except (AttributeError,MySQLdb.OperationalError):
			self.dbh=self._mysql_connect()
			try:
				cur=self.dbh.cursor()
				num=cur.execute(sql)
			except MySQLdb.MySQLError,e:
				num=-e.args[0]
		except MySQLdb.IntegrityError,e:
			num=-e.args[0]
		finally:
			return [cur,num]

	def query(self,sql):
		res=self._mysql_exec(sql)
		if res[1] > 0:
			rowAll=res[0].fetchall()
			res[0].close()
		else:
			rowAll=[]
		return [rowAll,res[1]]

	def write(self,sql):
		try:
			res=self._mysql_exec(sql)
			self.dbh.commit()
			if res[1] > 0:
				res[0].close()
		except:
			res=[-1,-1]
		return res[1]

	def multiple_write(self,sql):
		sqlList=sql.split(";")
		sqlList=[i for i in sqlList if i]
		if not sqlList:
			return -1
		try:
			res=self._mysql_exec(sqlList[0])
			for i in sqlList[1:]:
				num=res[0].execute(i)
				res[1]+=num
			self.dbh.commit()
			res[0].close()
		except:
			res=[-1,-1]
		return res[1]


	def close(self):
		try:
			if self.dbh:
				self.dbh.close()
		except:
			pass



