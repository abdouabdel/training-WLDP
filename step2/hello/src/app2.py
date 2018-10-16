#!/usr/bin/python

import argparse
from http.server import BaseHTTPRequestHandler,HTTPServer,SimpleHTTPRequestHandler
import os
import signal
import socketserver
import sys
import threading
from urllib.request import build_opener,ProxyHandler,HTTPError

class HelloServerRequestHandler(SimpleHTTPRequestHandler):

	# way in python to disable proxy auto-detection to make direct connections 
	NOPROXY_OPENER = build_opener(ProxyHandler({})) 

	# way in python to rely on system proxy config (env var, ...) 
	SYSTEMPROXY_OPENER = build_opener(ProxyHandler()) 

	def get_url(self, url, opener=None): 
		if (opener == None): 
			opener = HelloServerRequestHandler.NOPROXY_OPENER 
		try: 
			response = opener.open(url) 
			status = response.getcode(); 
			res = response.read() 
			return (200, res) 
		except HTTPError as e: 
			print("[error] Failed to get the adr '%s': %d %s" % (url, e.code, e.reason) )
		except: 
			print("[error] Failed to get '%s': %s" % (url, sys.exc_info()[1]) )
		return (502, 'Gateway Timeout') 

	def do_GET(self):
		self.protocol_version = 'HTTP/1.1'

		status = 404
		response = "Not Found"
		
		if (self.path == '/'):
			status, name = self.get_url('http://names:8080/') 
			response = 'Hello ' + name + '!\n' 
			
		if status == 502:
			response = "Failed to contact 'names' service"

		response = response.encode("utf8")
		self.send_response(status)
		self.send_header('Content-Type','text/plain; charset=utf-8')
		self.send_header('Content-Length', len(response) )
		self.end_headers()
		self.wfile.write(response)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
	"""Handle requests in a separate thread."""		
	daemon_threads = True

def main(args):
	print("starting hello server (pid=%s)..." % os.getpid())

	local_port = args.port # use port given (default is 8080). If 0, pick an available system port
	address = (args.address, local_port)

	HTTPServer.allow_reuse_address = True
	server = ThreadedHTTPServer(address, HelloServerRequestHandler)
	
	ip, local_port = server.server_address # find out what port we were given if 0 was passed
	print("listening on %s:%s" % (ip, local_port))

	def trigger_graceful_shutdown(signum, stack):
		# trigger shutdown from another thread to avoid deadlock
		t = threading.Thread(target=graceful_shutdown, args=(signum, stack))
		t.start()

	# handle graceful shutdown in a function we can easily bind on signals
	def graceful_shutdown(signum, stack):
		print("shutting down server...")
		try:
			server.shutdown();
		finally:
			print("server shut down.")

	signal.signal(signal.SIGTERM, trigger_graceful_shutdown)
	signal.signal(signal.SIGINT, trigger_graceful_shutdown)

	server.serve_forever()

if __name__ == '__main__':
	sys.tracebacklimit = 0

	parser = argparse.ArgumentParser(description = 'Launch the hello world server')
	parser.add_argument(
		'-a', '--address', metavar = '<address>',
		default = '127.0.0.1', dest = "address",
		help = 'listening address (default: 127.0.0.1)')
	parser.add_argument(
		'-p', '--port', metavar = '<port>', type = int,
		default = 8080, dest = "port",
		help = 'listening port (8080 if unspecified, random free port if 0)')

	args = parser.parse_args()
	main(args)
