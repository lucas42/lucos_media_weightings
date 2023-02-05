#! /usr/local/bin/python3
import json, sys, datetime, os, traceback, requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from func import getWeighting
verbose = False

if not os.environ.get("PORT"):
	sys.exit("\033[91mPORT not set\033[0m")
try:
	port = int(os.environ.get("PORT"))
except ValueError:
	sys.exit("\033[91mPORT isn't an integer\033[0m")

if not os.environ.get("MEDIA_API"):
	sys.exit("\033[91mMEDIA_API not set\033[0m")
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	sys.exit("\033[91mDon't include a trailing slash in the API url\033[0m")


def updateWeighting(track, currentDateTime, apiurl):
	verbose = False
	if ('weighting' in track):
		oldweighting = track['weighting']
	else:
		oldweighting = "Not set"
	weighting = getWeighting(track, currentDateTime)
	if (oldweighting != weighting):
		if verbose:
			print(json.dumps(track, indent=2))
		result = requests.put(apiurl+"/tracks/"+str(track['trackid'])+"/weighting", data=str(weighting), allow_redirects=False)
		if result.is_redirect:
			raise Exception("Redirect returned by server.  Make sure you're using the latest API URL.")
		elif result.ok:
			return result.text
		else:
			raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	else:
		return None


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
			"system": "lucos_media_weighting",
			"ci": {
				"circle": "gh/lucas42/lucos_media_weighting",
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
			track = json.loads(self.post_data)
		except json.decoder.JSONDecodeError as error:
			self.send_error(400, "Invalid json", str(error))
			return
		try:
			response = updateWeighting(track, datetime.datetime.utcnow(), apiurl)
			self.send_response(200, "OK")
			self.send_header("Content-type", "text/plain")
			self.end_headers()
			if response is None:
				self.wfile.write(bytes("Weighting Stayed the same", "utf-8"))
			else:
				self.wfile.write(bytes("Weighting Changed to " + response, "utf-8"))
		except Exception as error:
			traceback.print_exc()
			self.send_error(500, "Error updating weighting", str(error))


if __name__ == "__main__":
	server = HTTPServer(('', port), WeightingHandler)
	print("Server started on port %s" % (port))
	server.serve_forever()
