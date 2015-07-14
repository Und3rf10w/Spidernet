#!/usr/bin/env python
################################################
# SpiderNet 
#  By Wandering-Nomad (@wand3ringn0mad)
################################################
#
# This tool for educational uses only.  This  
#  code should not be used for systems that one
#  does not have authorization for.  All 
#  modification / rebranding / public use 
#  requires the authors concent 
#                                               
################################################

import paramiko
import interactive
import socket
import select
import os
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

class ForwardServer (SocketServer.ThreadingTCPServer):
		daemon_threads = True
		alow_reuse_address = True

class server(object):
	def __init__(self, hostname, port, username, password, local_tunport=CONST_LOCAL_TUNPORT):
		self.active = False
		self.hostname = hostname
		self.port = port
		self.username = username
		self.password = password
		self.connection_handle = ""
		self.local_tunport = local_tunport

	def details(self):
		print "Host: %s:%s (%s/%s)" % (self.hostname, self.port, self.username, self.password)
		print "Active: %s" % self.active

	def fulldetails(self):
		print "[+] Host           : %s:%s (%s/%s)" % (self.hostname, self.port, self.username, self.password)
		print " - Active          : %s" % self.active
		print " - R - Hostname    : %s" % self.execute_command('hostname')
		print " - R - IP Address  : %s" % self.execute_command("ifconfig eth0 | grep 'inet addr' | awk '{ print $2 }' | sed 's/addr://'" )
		print " - R - User        : %s" % self.execute_command('whoami')
		print " - uname           : %s" % self.execute_command('uname -a')
		print " - uptime          :%s"  % self.execute_command('uptime')

		
	def connect_host(self):
		if self.active:
			print "[x] Server Already Active"
			return 1
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((self.hostname, int(self.port)))
		except Exception, e:
			print "[x] Failed to Connect to %s " % self.hostname
			return 1
		
		try:
			self.connection_handle = paramiko.Transport(sock)
			try:
				self.connection_handle.start_client()
			except paramiko.SSHException:
				print '[x]  %s  SSH negotiation failed.' % self.hostname
				return 1
			
			try:						
				keys = paramiko.util.load_host_keys('ssh_keys/known_hosts')
			except IOError:
				print '[x] Unable to open host keys file'
				keys = {}		
			key = self.connection_handle.get_remote_server_key()
			if not keys.has_key(self.hostname):
				print '[x] %s  WARNING: Unknown host key!' % self.hostname
			elif not keys[self.hostname].has_key(key.get_name()):
				print '[x] %s  WARNING: Unknown host key!' % self.hostname
			elif keys[self.hostname][key.get_name()] != key:
				print '[x] %s  WARNING: Host key has changed!!!' % self.hostname
				return 1

			try:
				key = paramiko.RSAKey.from_private_key_file('ssh_keys/id_rsa')
			except paramiko.PasswordRequiredException:
				password = getpass.getpass('RSA key password: ')
				key = paramiko.RSAKey.from_private_key_file('ssh_keys/id_rsa', password)
				
			self.connection_handle.auth_publickey(self.username, key)		
			
			if not self.connection_handle.is_authenticated():
				manual_auth(self.username, self.hostname)
			if not self.connection_handle.is_authenticated():
				print '[x]  Authentication failed. :('
				self.connection_handle.close()
				return 1		
			
			self.active = True
			return 0



			
		except Exception, e:
		    print '[x]  Caught exception: ' + str(e.__class__) + ': ' + str(e)
		    try:
		        self.connection_handle.close()
		    except:
		        pass
		    return 1			
			
			
	def execute_command(self,command):
		stdout_data = []
		stderr_data = []
		
		session = self.connection_handle.open_session()
		session.exec_command(command)

		while True:
			if session.recv_ready():
				stdout_data.append(session.recv(4096))
			if session.recv_stderr_ready():
				stderr_data.append(session.recv_stderr(4096))
			if session.exit_status_ready():
				break
			
		return ''.join(stdout_data).rstrip()

	def shell(self):
		if not self.active:
			print "[x] Server Already Active"
			return 1
		session = self.connection_handle.open_session()
		session.get_pty()
		session.invoke_shell()
		interactive.interactive_shell(session)
		session.close()

	def shutdown(self):
		if not self.active:
			print "[x] %s Server Not Active" % self.hostname
			return 1
		self.connection_handle.close()
		self.active = False
		print "[x] %s server shutdown" % self.hostname

	def establish_tunnel(self):
		if not self.active:
			print "[x] %s Server Not Active" % self.hostname
			return 1
		stdout_data = []
		stderr_data = []
		class Handler(SocketServer.BaseRequestHandler):
				def handle(self):
					try:
							channel = self.ssh_transport.open_channel('direct-tcpip', (self.hostname, self.port), self.request.getpeername())
					except Exception as error:
							print "[ERROR]: Incoming request to %s:%d failed: %s" % (self.hostname, self.port, repr(e))
							return 1
					if channel is None:
							print "[ERROR]: Incoming request to %s:%d was rejected by the SSH server." %(self.hostname, self.port)
							return 1
					print "[x] Tunnel established: %r -> %r -> %r" %(self.request.getpeername(), chan.getpeername(), (self.hostname, self.port))

					while True:
						r, w, x = select.select([self.request, channel], [], [])
						if self.request in r:
							data = self.request.recv(1024)
							if len(data) == 0:
								break
							channel.send(data)
						if channel in r:
							data = channel.recv(1024)
							if len(data) == 0:
								break
							self.request.send(data)
					peername = self.request.getpeername()
					channel.close()
					self.request.close()
					print "[x] Tunnel closed: %r" % peername

	#def forward_tunnel(self.local_tunport, self.hostname, self.port, transport):
	def forward_tunnel(self, transport):
		class SubHanler(Handler):
			self.hostname = hostname
			self.port = port
			ssh_transport = transport
		ForwardServer(('', self.local_tunport), SubHander).serve_forever()

