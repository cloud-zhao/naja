# naja
	用来收集并管理主机的自定义服务

#### plugins 
	在此目录下实现TRun或DRun类既可以动态执行 
#### config
	这个模块提供从远程更新配置文件的能力，可以用于更新代码，更新的代码将会被RunPlugin动态加载执行
#### plugin
	这个模块提供动态加载代码并执行的能力
#### dependent
	psutil,MySQL,kafka-python
