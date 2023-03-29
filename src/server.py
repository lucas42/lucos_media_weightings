#! /usr/local/bin/python3
import json, sys, os, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from media_api import updateWeighting

if not os.environ.get("PORT"):
	sys.exit("\033[91mPORT not set\033[0m")
try:
	port = int(os.environ.get("PORT"))
except ValueError:
	sys.exit("\033[91mPORT isn't an integer\033[0m")

class WeightingHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		if (self.path == "/_info"):
			self.infoController()
		else:
			self.send_error(404, "Page Not Found")
		self.wfile.flush()
		self.connection.close()
	def do_POST(self):
		self.post_data = self.rfile.read(int(self.headers['Content-Length']))
		if (self.path == "/weight-track"):
			self.singleTrackController()
		else:
			self.send_error(404, "Page Not Found")
		self.wfile.flush()
		self.connection.close()
	def infoController(self):
		output = {
			"system": "lucos_media_weightings",
			"ci": {
				"circle": "gh/lucas42/lucos_media_weightings",
			},
			"checks": {
			},
			"metrics": {
			},
			"network_only": True,
			"show_on_homepage": False,
		}
		self.send_response(200)
		self.send_header("Content-type", "application/json")
		self.end_headers()
		self.wfile.write(bytes(json.dumps(output, indent="\t")+"\n\n", "utf-8"))
	def singleTrackController(self):
		try:
			event = json.loads(self.post_data)
		except json.decoder.JSONDecodeError as error:
			self.send_error(400, "Invalid json", str(error))
			return
		try:
			response = updateWeighting(event["track"])
			self.send_response(200, "OK")
			self.send_header("Content-type", "text/plain")
			self.end_headers()
			self.wfile.write(bytes(response, "utf-8"))
		except Exception as error:
			traceback.print_exc()
			self.send_error(500, "Error updating weighting", str(error))


if __name__ == "__main__":
	server = HTTPServer(('', port), WeightingHandler)
	print("Server started on port %s" % (port))
	server.serve_forever()
