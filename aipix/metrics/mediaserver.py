#!/usr/bin/python3
import time
import json
import glob
import os
import re
from subprocess import check_output

PageSize = int(os.popen('getconf PAGE_SIZE').readline().strip())
ClkTck = int(os.popen('getconf CLK_TCK').readline().strip())
PathToProcName = "/opt/navekscreen/media-server/"
ProcName = "media-server"
ProcPid = 0

def div(prev, now, ts=1):
	if ts:
		return int((now - prev)/ts)
	return 0

def fetchJson(name,default):
	try:
		with open('/tmp/{}.{}.json'.format(ProcName,name)) as fd:
			return json.load(fd)
	except Exception as x:
		pass
	return default

def putJson(name, data):
	try:
		with open('/tmp/{}.{}.json'.format(ProcName,name),'w') as fd:
			json.dump(data, fd)
	except Exception as x:
		pass

def fetchMetrics(name,data):
	data["@timestamp"] = int(time.time())
	data["@pid"] = pid()
	prev = fetchJson(name,data)
	if "@pid" not in prev or prev["@pid"] != data["@pid"]:
		prev = {**data}
	putJson(name,data)
	prev["#"] = data["@timestamp"] - prev["@timestamp"]
	data.pop('@timestamp')
	data.pop('@pid')
	return prev

def pid():	
	global ProcPid
	if ProcPid:
		return ProcPid
	else:
		streams = list(map(int,check_output(["pidof",ProcName]).split()))
		ProcPid = streams[-1]
		return ProcPid
	
def sysuptime():
	with open("/proc/uptime") as f:
		contents = f.read()
	return int(float(contents.strip().split(' ')[0]))

def file(path):
	try:
		with open(path) as f:
			contents = f.read()
		return contents.splitlines()
	except Exception as x:
		pass
	return []

def proc(path):
	return file("/proc/{0}/{1}".format(pid(),path))

def map_view(arr, sep):
	view = {}
	for line in arr:
		cols = line.split(sep)
		view[cols[0].strip()] = cols[1].strip()
	return view

def arr_view(line, sep):
	return [i.strip() for i in line.split(sep)]

def io():
	inf = proc("io")
	if inf:
		map = map_view(inf,':')
		metrics = {'read_ops': int(map['syscr']), 'write_ops': int(map['syscw']),
			'read_bytes': int(map['read_bytes']),'write_bytes': int(map['write_bytes']), }
		prev = fetchMetrics("io",metrics)
		metrics['read_ops_d'] = div(prev["read_ops"],metrics["read_ops"])
		metrics['write_ops_d'] = div(prev["write_ops"],metrics["write_ops"])
		metrics['read_bytes_d'] = div(prev["read_bytes"],metrics["read_bytes"])
		metrics['write_bytes_d'] = div(prev["write_bytes"],metrics["write_bytes"])
		return metrics
	return False
	#return {'read_ops': 0, 'write_ops': 0,'read_bytes': 0,'write_bytes': 0, }

def statm():
	inf = proc("statm")
	if inf:
		map = arr_view(inf[0], ' ')
		return {'vmsize': int(map[0]) * PageSize,'vmrss': int(map[1]) * PageSize,
			'shared': int(map[2]) * PageSize, 'data': int(map[3]) * PageSize}
	return False
	#return {'vmsize': 0,'vmrss': 0,'shared': 0, 'data': 0 }

def stat():
	inf = proc("stat")
	sinf = file('/proc/stat')
	ver="0.0.0"
	osver = os.uname()
	with os.popen(PathToProcName+"{} -vs".format(ProcName)) as f:
		ver = f.readline()
	with os.popen(PathToProcName+"{} -vb".format(ProcName)) as f:
		ver += "." + f.readline()
	with os.popen(PathToProcName+"{} -vr".format(ProcName)) as f:
		ver += "-" + f.readline()
	old = fetchJson('ver',{"pid": 0,"restarts": 0})
	if old["pid"] != pid():
		old["restarts"] += 1
		old["pid"] = pid()
		putJson("ver",old)
	if inf:
		map = arr_view(inf[0], ' ')
		smap = arr_view(sinf[0], ' ')
		pcpu = int((int(map[13]) + int(map[14]) + int(map[15]) + int(map[16])))
		tcpu = int((int(smap[2]) + int(smap[3]) + int(smap[4])  + int(smap[7]) + int(smap[8])))
		tiowait = int(smap[6])
		prev = fetchMetrics('cpu',{"pcpu": pcpu,"tcpu": tcpu,"iow": tiowait})
#		putJson('cpu',{"pcpu": pcpu,"tcpu": tcpu, "iow": tiowait,'pid': pid()})
		return {'pid': int(map[0]), # 'proc.state': str(map[2]),
			'cpu': div(prev['pcpu'],pcpu,prev['#']), 'total': div(prev['tcpu'],tcpu,prev['#']),
			'iowait': div(prev['iow'],tiowait,prev['#']),
			"version": "\"{}\"".format(ver),"restarts": old["restarts"],"os": "\"{0}-{1}\"".format(osver[2],osver[0]),
			'uptime': sysuptime() - int(int(map[21])/ClkTck) }

def version():
	ver="0.0.0"
	osver = os.uname()
	with os.popen("/proc/{0}/exe -vs".format(pid())) as f:
		ver = f.readline()
	with os.popen("/proc/{0}/exe -vb".format(pid())) as f:
		ver += "." + f.readline()
	with os.popen("/proc/{0}/exe -vr".format(pid())) as f:
		ver += "-" + f.readline()
	old = fetchJson('ver',{"pid": pid(),"restarts": 0})
	if old["pid"] != pid():
		old["restarts"] += 1
		putJson("ver",old)

	return {"version": "\"{}\"".format(ver),"restarts": old["restarts"],"os": "\"{0}-{1}\"".format(osver[2],osver[0])
		}

def proc_task(fln, tasks):
	task = file("{0}/comm".format(fln))[0].split('#')
	st = arr_view(file("{0}/stat".format(fln))[0], ' ')
	if task[0] in tasks:
		tasks[task[0]]["count"] += 1
		tasks[task[0]]["cpu"] += int(st[13]) + int(st[14]) + int(st[15]) + int(st[16])
	else:
		tasks[task[0]] = {"count": 1, "cpu":  int(st[13]) + int(st[14]) + int(st[15]) + int(st[16]) }
	return tasks


def tasks():
	id = pid()
	tasks = {}
	result = {}
	for th in glob.glob("/proc/{0}/task/*".format(id)):
		tasks = proc_task(th,tasks)
	prev = fetchMetrics('tasks',tasks)
	for t, v in tasks.items():
		tasks[t]['cpu_d'] = div(prev[t]['cpu'],v['cpu'],prev['#'])
	return tasks

def net():
	rows = proc("net/netstat")
	if rows:
		tcpinf = dict(zip (arr_view(rows[0],' '), arr_view(rows[1],' ')))
		ipinf = dict(zip (arr_view(rows[2],' '), arr_view(rows[3],' ')))
		return {"listen_drops": int(tcpinf["ListenDrops"]),
			"abort": int(tcpinf["TCPAbortOnMemory"]) + int(tcpinf["TCPAbortOnTimeout"]) + int(tcpinf["TCPAbortOnClose"]) + int(tcpinf["TCPAbortOnData"]),
			"undo": int(tcpinf["TCPFullUndo"]) + int(tcpinf["TCPDSACKUndo"]) + int(tcpinf["TCPPartialUndo"])  + int(tcpinf["TCPLossUndo"]),
			"slow": int(tcpinf["TCPSlowStartRetrans"]),"in": int(ipinf["InOctets"]),"out": int(ipinf["OutOctets"]) }

def sockets():
	rows = proc("net/tcp")[1::]
	count = 0
	ports = {"in":
			{"0": {"conn":0,'port':0,"rxq":0, "txq":0,"ss_estab": 0, "ss_close_wait":0, "ss_closed": 0,"ss_slow":0,"ss_very_slow":0}},
		"out":
			{"0": {"conn":0,'port':0,"rxq":0, "txq":0,"ss_estab": 0, "ss_close_wait":0, "ss_closed": 0,"ss_slow":0,"ss_very_slow":0}}}
	if rows:
		for so in rows:
			match = re.search(r"^\s*\d+:\s*(\w+):(\w+)\s+(\w+):(\w+)\s+(\w+)\s+(\w+):(\w+)\s+(\w+):(\w+)\s+(\w+)\s+(\d+)\s+(\d+).*\s+(-?\d+)", so, re.MULTILINE)
			if match.group(11) != "0":
				continue
			if match and match.group(1) == "00000000":
				if match.group(2) not in ports["in"]:
					ports["in"][match.group(2)] = {"conn":0,"port":int(match.group(2),16),"rxq":0, "txq":0,"ss_estab": 0, "ss_close_wait":0, "ss_closed": 0,"ss_slow":0,"ss_very_slow":0}
			elif match.group(5) != "0A":
				ss_estab = match.group(5) in ['01','02','03','0С']
				ss_close_wait = match.group(5) == "08"
				ss_closed = match.group(5) not in ['01','02','03','0С', "08"]
				slow = int(match.group(13))
				is_slow = slow > 300
				is_very_slow = slow > 100 and slow <= 300
				if match.group(2) in ports["in"]:
					ports["in"][match.group(2)]["conn"] += 1
					ports["in"][match.group(2)]["rxq"] += int(match.group(7),16)
					ports["in"][match.group(2)]["txq"] += int(match.group(6),16)
					ports["in"][match.group(2)]["ss_estab"] += ss_estab
					ports["in"][match.group(2)]["ss_close_wait"] += ss_close_wait
					ports["in"][match.group(2)]["ss_closed"] += ss_closed
					ports["in"][match.group(2)]["ss_slow"] += is_slow
					ports["in"][match.group(2)]["ss_very_slow"] += is_very_slow
					ports["in"]['0']["conn"] += 1
					ports["in"]['0']["rxq"] += int(match.group(7),16)
					ports["in"]['0']["txq"] += int(match.group(6),16)
					ports["in"]['0']["ss_estab"] += ss_estab
					ports["in"]['0']["ss_close_wait"] += ss_close_wait
					ports["in"]['0']["ss_closed"] += ss_closed
					ports["in"]['0']["ss_slow"] += is_slow
					ports["in"]['0']["ss_very_slow"] += is_very_slow
				elif match.group(4) in ports["out"]:
					ports["out"][match.group(4)]["conn"] += 1
					ports["out"][match.group(4)]["rxq"] += int(match.group(7),16)
					ports["out"][match.group(4)]["txq"] += int(match.group(6),16)
					ports["out"][match.group(4)]["ss_estab"] += ss_estab
					ports["out"][match.group(4)]["ss_close_wait"] += ss_close_wait
					ports["out"][match.group(4)]["ss_closed"] += ss_closed
					ports["out"][match.group(4)]["ss_slow"] += is_slow
					ports["out"][match.group(4)]["ss_very_slow"] += is_very_slow
					ports["out"]['0']["conn"] += 1
					ports["out"]['0']["rxq"] += int(match.group(7),16)
					ports["out"]['0']["txq"] += int(match.group(6),16)
					ports["out"]['0']["ss_estab"] += ss_estab
					ports["out"]['0']["ss_close_wait"] += ss_close_wait
					ports["out"]['0']["ss_closed"] += ss_closed
					ports["out"]['0']["ss_slow"] += is_slow
					ports["out"]['0']["ss_very_slow"] += is_very_slow
				elif match.group(4) != '0000':
					ports["out"][match.group(4)] = {"conn":1,"port":int(match.group(4),16),"rxq":0, "txq":0,"ss_estab": 0,"ss_close_wait":0, "ss_closed": 0,"ss_slow":0,"ss_very_slow":0}
				count += 1
	if count == 0:
		return False
	return ports