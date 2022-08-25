#! /usr/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import time

bindIP = "192.168.2.26"
bindPort = 8123
hassIP = "192.168.2.8"

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
    	if '?token=' in self.path:
    		path, token = self.path.split('?token=')
    	else:
    		path = self.path
    		token = None

    	if token:
    		headers = {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}
    	else:
    		headers = None

    	requestURL = 'http://{}:8123{}'.format(hassIP, path)
    	print(requestURL, headers)
    	response = requests.get(requestURL, headers=headers)

    	self.send_response(response.status_code)
    	self.send_header("Content-type", "application/json")
    	self.end_headers()
    	self.wfile.write(bytes(response.text, 'utf-8'))

    def do_POST(self):
    	if '?token=' in self.path:
    		path, token = self.path.split('?token=')
    	else:
    		path = self.path
    		token = None

    	if token:
    		headers = {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}
    	else:
    		headers = None

    	dataLength = int(self.headers.get('Content-Length'))
    	data = self.rfile.read(dataLength)

    	requestURL = 'http://{}:8123{}'.format(hassIP, path, data=data)
    	print(requestURL, headers)
    	response = requests.post(requestURL, headers=headers, data=data)

    	self.send_response(response.status_code)
    	self.send_header("Content-type", "application/json")
    	self.end_headers()
    	self.wfile.write(bytes(response.text, 'utf-8'))

if __name__ == "__main__":        
    webServer = HTTPServer((bindIP, bindPort), MyServer)
    print("Server started http://%s:%s" % (bindIP, bindPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
