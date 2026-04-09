#! /usr/local/bin/python3
import json, sys, os, traceback
from media_api import updateWeighting
from waitress import serve

from log_util import info, error

if not os.environ.get("PORT"):
	error("PORT not set")
	sys.exit(1)
try:
	port = int(os.environ.get("PORT"))
except ValueError:
	error("PORT isn't an integer")
	sys.exit(1)

def _get_valid_keys():
	"""Parse CLIENT_KEYS env var (semicolon-separated name=value pairs) into a set of valid tokens."""
	client_keys_str = os.environ.get("CLIENT_KEYS", "")
	if not client_keys_str:
		return set()
	return {pair.split("=", 1)[1] for pair in client_keys_str.split(";") if "=" in pair}

def is_authorised(environ):
	"""Return True if the request has a valid Bearer token, or if CLIENT_KEYS is not configured.

	During the migration phase (Phase 1), requests without an Authorization header are also
	accepted to maintain backwards compatibility with Loganne before it starts sending tokens.
	"""
	valid_keys = _get_valid_keys()
	if not valid_keys:
		return True
	auth_header = environ.get("HTTP_AUTHORIZATION", "")
	if not auth_header:
		return True  # Accept unauthenticated during Phase 1 migration
	if not auth_header.startswith("Bearer "):
		return False
	token = auth_header[len("Bearer "):]
	return token in valid_keys

def app(environ, start_response):
	method = environ["REQUEST_METHOD"]
	path = environ["PATH_INFO"]
	info(f"{method} {path}")

	if method == "GET" and path == "/_info":
		return info_controller(start_response)
	elif method == "POST" and path == "/weight-track":
		return weight_track_controller(environ, start_response)
	else:
		start_response("404 Not Found", [("Content-Type", "text/plain")])
		return [b"Not Found"]

def info_controller(start_response):
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
	body = bytes(json.dumps(output, indent="\t") + "\n\n", "utf-8")
	start_response("200 OK", [("Content-Type", "application/json")])
	return [body]

def weight_track_controller(environ, start_response):
	if not is_authorised(environ):
		start_response("401 Unauthorized", [("Content-Type", "text/plain"), ("WWW-Authenticate", "Bearer")])
		return [b"Invalid API Key"]
	try:
		length = int(environ.get("CONTENT_LENGTH") or 0)
		post_data = environ["wsgi.input"].read(length)
		event = json.loads(post_data)
	except (ValueError, json.decoder.JSONDecodeError) as err:
		start_response("400 Bad Request", [("Content-Type", "text/plain")])
		return [bytes(str(err), "utf-8")]
	try:
		response = updateWeighting(event["track"])
		start_response("200 OK", [("Content-Type", "text/plain")])
		return [bytes(response, "utf-8")]
	except Exception as err:
		traceback.print_exc()
		error(f"Error updating weighting: {str(err)}")
		start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
		return [bytes(str(err), "utf-8")]

if __name__ == "__main__":
	info("Server started on port %s" % (port))
	serve(app, host="0.0.0.0", port=port)
