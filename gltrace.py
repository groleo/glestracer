#! /usr/bin/python

import getopt
import os
import signal
import socket
import string
import sys
import time

import testrunner.adb_interface
import testrunner.logger
import testrunner.gltrace_pb2
from struct import *



signal_raised = False
adb = testrunner.adb_interface.AdbInterface()



def do_help(ret):
	print "usage: gltrace.py --trace <application> -o <outputfile> | -i <inputfile> | -s <serialno>"
	sys.exit(ret)



def kill_app(app):
	o = adb.SendShellCommand("ps|grep " + app)
	if o != '':
		pid = string.split(o)[1]
		adb.SendShellCommand("kill " + pid)



def signal_handler(signal, frame):
	global signal_raised
	signal_raised = True
	print "\nexiting..."



def do_trace(tracedapp,outputfile):
	testrunner.logger.SetVerbose(True)

	adb.SendShellCommand("setprop debug.egl.trace ''");
	adb.SendShellCommand("setprop debug.egl.debug_proc %s" % os.path.dirname(tracedapp))
	adb.SendShellCommand("setprop debug.egl.debug_portname 'gltrace'")

	#forward local port 9222 to remote unix socket "gltrace"
	adb.SendCommand("forward tcp:9222 localabstract:gltrace")

	#start the settings app
	adb.SendShellCommand("am start  %s" % tracedapp)
	# connect to gltrace
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	s.connect( ('localhost', 9222) )

	total_bytes=0
	f=open(outputfile,"wb")
	print "Tracing started"
	while signal_raised == False:
		# read protobuf chunk size
		buf=""
		rd=0
		while rd < 4:
			r=s.recv(4-rd)
			if len(r)==0:
				print "cannot read"
				break
			rd+=len(r)
			buf+=r
		# unpack it as little-endian
		plen=unpack("<I",buf)[0]

		# read protobuf
		buf=""
		rd=0
		while rd < plen:
			r=s.recv(plen-rd)
			if len(r)==0:
				break
			rd+=len(r)
			buf+=r

		# pack it as big-endian
		f.write(pack(">I",plen))

		# write protobuf to disk
		f.write(buf)
		total_bytes+=plen
		sys.stdout.write( "\rcaptured: %04f MB" % (total_bytes/(1024.0*1024)) )

	f.flush()
	f.close()
	print "\ntotal bytes read:%d" % total_bytes



def do_view(inputfile):
	glmsg = testrunner.gltrace_pb2.GLMessage()
	f=open(inputfile,"rb")
	i=0
	while signal_raised == False:
		buf = f.read(4)
		if len(buf) != 4:
			break
		size = unpack(">I",buf)[0]

		buf = f.read(size)
		if len(buf) != size:
			break

		glmsg.ParseFromString(buf)
		function = glmsg.DESCRIPTOR.enum_types[0].values_by_number[glmsg.function].name
		print "%d %s duration=%d" % (glmsg.threadtime, function,glmsg.duration)
		i+=1



def main(argv):
	inputfile = ''
	outputfile = ''
	tracedapp = ''

	signal.signal(signal.SIGINT, signal_handler)

	try:
		opts, args = getopt.getopt(argv,"hi:o:t:s:",["ifile=","ofile=","trace=","serial="])
	except getopt.GetoptError:
		do_help()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			do_help(0)
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-o", "--ofile"):
			outputfile = arg
		elif opt in ("-t", "--trace"):
			tracedapp = arg
		elif opt in ("-s", "--serial"):
			adb.SetTargetSerial(arg)

	if inputfile != '':
		do_view(inputfile)
	elif tracedapp != '' and outputfile != '':
		kill_app(os.path.dirname(tracedapp))
		do_trace(tracedapp,outputfile)
	else:
		do_help(2)



if __name__ == "__main__":
   main(sys.argv[1:])
