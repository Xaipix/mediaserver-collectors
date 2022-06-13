#!/usr/bin/python3
import sys
import aipix
from aipix.metrics import mediaserver as ms
from aipix.metrics import influx as influx

ms.ProcName = "media-server"

if __name__ == '__main__':
	if sys.argv[1] == 'io':
		result_io = ms.io()
		if result_io != False:
			influx("mediaserver.io",result_io,{"host":aipix.host_id()})
	elif sys.argv[1] == 'version':
		result_ver = ms.version()
		if result_ver != False:
			influx("mediaserver.version",result_ver,{"host":aipix.host_id()})
	elif sys.argv[1] == 'memory':
		result_mem = ms.statm()
		if result_mem != False:
			influx("mediaserver.memory",result_mem,{"host":aipix.host_id()})
	elif sys.argv[1] == 'proc':
		result_ver = ms.stat()
		if result_ver != False:
			influx("mediaserver.proc",result_ver,{"host":aipix.host_id()})
	elif sys.argv[1] == 'tasks':
		for k, v in ms.tasks().items():
			influx("mediaserver.tasks",v,{"host":aipix.host_id(),"task":k})
	elif sys.argv[1] == 'sockets':
		ss = ms.sockets()
		if ss != False:
			for k, v in ss['in'].items():
				influx("mediaserver.incomming",v,{"host":aipix.host_id(),"_port":v['port']})
			for k, v in ss['out'].items():
				influx("mediaserver.outgoing",v,{"host":aipix.host_id(),"_port":v['port']})
