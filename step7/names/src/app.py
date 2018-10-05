#!/usr/bin/python

import argparse
import BaseHTTPServer
import names
import os
import signal
import SimpleHTTPServer
import SocketServer
import sys
import threading
import ConfigParser
import urlparse

class HelloServerRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

	def do_GET(self):
		self.protocol_version = 'HTTP/1.1'

		status = 200
		
		# retrieve path and query params from url
		print "url=%s" % (self.path)
		from urlparse import urlparse
		url_path = urlparse(self.path).path
		print "path=%s" % (url_path)
		url_query = urlparse(self.path).query
		print "query=%s" % (url_query)
		
		# Read the property file 
		config = ConfigParser.ConfigParser()
		config.read('config/config.ini')
		
		if (url_path == '/'):
			response = names.get_full_name()
		elif (url_path == '/male'):
			response = names.get_full_name(gender='male')
		elif (url_path == '/female'):
			response = names.get_full_name(gender='female')
		elif (url_path == '/bestactor'):
		
			# retrieve the env var key
			key = os.environ['PROPERTY_KEY']
			print "This is the value of the key present in your `config.ini` into your configmap `name-config`: %s" % (key)
			response = config.get('BESTACTOR',key)
			
		elif (url_path == '/private'):
		
			# split query param to get the user and pwd params
			query_components = dict(qc.split("=") for qc in url_query.split("&"))
			usr = query_components["usr"]
			pwd = query_components["pwd"]
			print "query usr=%s" % (usr)
			print "query pwd=%s" % (pwd)
			
			# retrieve the username and password secret env var
			username = os.environ['USERNAME']
			password = os.environ['PASSWORD']
			print "configmap username=%s" % (username)
			print "configmap password=%s" % (password)

			if(password == pwd and username == usr):
				response = config.get('PRIVATE','fact')
			else:
				status = 401
				response = 'Unauthorized to access to this resource'
			
		else:
			status = 404
			response = "Not Found"
		
		response = response.encode("utf8")
		self.send_response(status)
		self.send_header('Content-Type','text/plain; charset=utf-8')
		self.send_header('Content-Length', len(response) )
		self.end_headers()
		self.wfile.write(response)
		self.wfile.write('\n')

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	"""Handle requests in a separate thread."""		
	daemon_threads = True

def main(args):
	print "starting names server (pid=%s)..." % os.getpid()

	local_port = args.port # use port given (default is 8080). If 0, pick an available system port
	address = (args.address, local_port)

	BaseHTTPServer.HTTPServer.allow_reuse_address = True
	server = ThreadedHTTPServer(address, HelloServerRequestHandler)
	
	ip, local_port = server.server_address # find out what port we were given if 0 was passed
	print "listening on %s:%s" % (ip, local_port)

	def trigger_graceful_shutdown(signum, stack):
		# trigger shutdown from another thread to avoid deadlock
		t = threading.Thread(target=graceful_shutdown, args=(signum, stack))
		t.start()

	# handle graceful shutdown in a function we can easily bind on signals
	def graceful_shutdown(signum, stack):
		print "shutting down server..."
		try:
			server.shutdown();
		finally:
			print "server shut down."

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
