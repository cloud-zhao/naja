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
#### usage
```
	#使用代码如下
	#配置文件是properties格式的
	#配置文件内容为
	#config.file.[插件类名]=[传递给类的配置文件]
	import sys
	from naja.plugin import RunPlugin
	
	def main(args):
		rp = RunPlugin(remoteServer=args[0],configFile=args[1])
		rp.run()

	if __name__ == '__main__':
		if len(sys.argv) == 3:
			main(sys.argv[1:])
		else:
			print "Usage: python %s remoteServer configFile" %sys.argv[0]

```
