#drop database if exists naja;
#create database naja default character set utf8;

#grant all privileges on naja.* to naja@'%' identified by 'naja';
#grant all privileges on naja.* to naja@'localhost' identified by 'naja';
#flush privileges;

use naja;


#主机表
#主机名必须是全局唯一的,可以更新变更,变更后也必须全局唯一
drop table if exists hosts;
create table hosts (
	host_id		varchar(36) not null,
	host_name	varchar(255) not null,
	timestamp	varchar(10) not null,
	primary key (host_id)
);
#insert into hosts (host_id,host_name,timestamp) values
#("ccb7e38c-ab11-470c-bd49-52a5500ed568","hadoop43","root","1234567890");

#主机密码表
drop table if exists password;
create table password (
	host_id		varchar(36) not null,
	host_user	varchar(50) not null,
	passwd		varchar(255) ,
	public_key	varchar(1024) ,
	timestamp	varchar(10),
	primary key (host_id,host_user)
);

#主机ip表
drop table if exists ips;
create table ips (
	host_id		varchar(36) not null,
	host_ifname	varchar(36) not null,
	host_ip		varchar(16) not null,
	timestamp	varchar(10) not null,
	primary key (host_id,host_ifname)
);
#insert into hosts_ip (host_id,host_ifname,host_ip) values
#("ccb7e38c-ab11-470c-bd49-52a5500ed568","em3","42.62.88.226");

#主机角色表
drop table if exists roles;
create table roles (
	host_id		varchar(36) not null,
	host_role	varchar(255) not null,
	table_name	varchar(255),
	timestamp	varchar(10) not null,
	primary key (host_id,host_role)
);
#table_name 存储主机角色对应的信息的表,具体表由指定探测某种角色需要上报的信息决定。
#host_role in enum("flume","mysql","kafka","datanode","namenode",...,...)
#insert into roles_info (host_id,host_role,table_name,timestamp) values
#("ccb7e38c-ab11-470c-bd49-52a5500ed568","flume","role_flume","1234567890");
#insert into roles_info (host_id,host_role,timestamp) values
#("ccb7e38c-ab11-470c-bd49-52a5500ed568","mysql","1449900992");

#主机内存表
drop table if exists mem;
create table mem (
	host_id		varchar(36) not null,
	total		varchar(20) not null,
	used		varchar(20) not null,
	free		varchar(20) not null,
	shared		varchar(20) not null,
	buffer		varchar(20)	not null,
	cached		varchar(20)	not null,
	timestamp	varchar(10) not null
);

#主机cpu表
drop table if exists cpu;
create table cpu (
	host_id		varchar(36) not null,
	userd		varchar(5)	not null,
	sys			varchar(5)	not null,
	idle		varchar(5)	not null,
	timestamp	varchar(10)	not null
);

#主机磁盘表
drop table if exists disk;
create table disk (
	host_id		varchar(36) not null,
	mount		varchar(255) not null,
	device		varchar(255) not null,
	fstype		varchar(255) not null,
	total		varchar(20) not null,
	used		varchar(20)	not null,
	io_read		varchar(10)	not null,
	io_write	varchar(10)	not null,
	timestamp	varchar(10) not null
);

#主机网络io表
drop table if exists net_io;
create table net_io (
	host_id		varchar(36) not null,
	host_ifname	varchar(255) not null,
	send		varchar(40) not null,
	receive		varchar(40) not null,
	link_num	varchar(10)	not null,
	total_link	varchar(10) not null,
	timestamp	varchar(10) not null
);



#flume角色表,此表是在添加新角色探测的时候需要添加创建的新表
#表名必须以"role_角色名"为名称且包含host_id字段
drop table if exists role_flume;
create table role_flume (
	host_id		varchar(36) not null,
	instance	varchar(255) not null,
	source		varchar(1024),
	channel		varchar(1024),
	sink		varchar(1024),
	timestamp	varchar(10) not null,
	primary key (host_id,instance)
);

