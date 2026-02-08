#! /usr/local/bin/python3
import json, sys, os, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from media_api import updateWeighting

from log_util import info, error

if not os.environ.get("PORT"):
	error("PORT not set")
	sys.exit(1)
try:
	port = int(os.environ.get("PORT"))
except ValueError:
	error("PORT isn't an integer")
	sys.exit(1)

class WeightingHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		info(f"GET {self.path}")
		if (self.path == "/_info"):
			self.infoController()
		else:
			self.send_error(404, "Page Not Found")
		self.wfile.flush()
		self.connection.close()
	def do_POST(self):
		info(f"POST {self.path}")
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
		except Exception as err:
			traceback.print_exc()
			error(f"Error updating weighting: {str(err)}")
			self.send_error(500, "Error updating weighting", str(err))


if __name__ == "__main__":
	server = HTTPServer(('', port), WeightingHandler)
	info("Server started on port %s" % (port))
	server.serve_forever()
