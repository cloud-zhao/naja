import sys
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
