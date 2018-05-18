import sys

def try_import(from_name,import_name,try_name):
	g=globals()
	try:
		g[import_name]=getattr(__import__(from_name),import_name)
	except ImportError:
		g[import_name]=getattr(__import__(try_name),import_name)

#try_import("naja.util","MyTools",".util")
#try_import("naja.plugin","RunPlugin",".plugin")
#try_import("naja.plugins.collect","CollectSysMsg",".plugins.collect")
from naja.util import MyTools
from naja.plugin import RunPlugin
from naja.plugins.collect import CollectSysMsg

def main(args):
	rp = RunPlugin(remoteServer=args[0],configFile=args[1])
	rp.run()


if __name__ == '__main__':
	if len(sys.argv) == 3:
		main(sys.argv[1:])
	else:
		print "python %s remote_server config_file" %sys.argv[0]
