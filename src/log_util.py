from datetime import datetime
import os, sys

# ANSI colour codes used in log output
_COLOR_INFO  = "\033[92m"  # green
_COLOR_WARN  = "\033[93m"  # yellow
_COLOR_ERROR = "\033[91m"  # red
_COLOR_RESET = "\033[0m"

def _log(level, message, color):
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	formatted_message = f"[{timestamp}] {color}{level} {message}{_COLOR_RESET}"
	print(formatted_message, flush=True)

def info(message):
	_log("INFO", message, _COLOR_INFO)

def warn(message):
	_log("WARN", message, _COLOR_WARN)

def error(message):
	_log("ERROR", message, _COLOR_ERROR)

def debug(message):
	"""Log a debug message. Only output if LOG_LEVEL=debug is set in the environment."""
	if os.environ.get("LOG_LEVEL", "").lower() == "debug":
		_log("DEBUG", message, _COLOR_INFO)
