from datetime import datetime
import os, sys

# Severity order — lower index = lower severity.
# _log() suppresses messages below the level named in LOG_LEVEL (default: INFO).
# e.g. LOG_LEVEL=WARN suppresses INFO and DEBUG; LOG_LEVEL=DEBUG enables everything.
_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR"]

# ANSI colour codes, keyed by level name
_COLORS = {
	"DEBUG": "\033[92m",  # green
	"INFO":  "\033[92m",  # green
	"WARN":  "\033[93m",  # yellow
	"ERROR": "\033[91m",  # red
}
_COLOR_RESET = "\033[0m"

def _log(level, message):
	configured = os.environ.get("LOG_LEVEL", "INFO").upper()
	min_index = _LEVELS.index(configured) if configured in _LEVELS else _LEVELS.index("INFO")
	if _LEVELS.index(level) < min_index:
		return
	color = _COLORS.get(level, _COLORS["INFO"])
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	formatted_message = f"[{timestamp}] {color}{level} {message}{_COLOR_RESET}"
	print(formatted_message, flush=True)

def debug(message):
	"""Log a DEBUG-level message. Suppressed unless LOG_LEVEL=DEBUG."""
	_log("DEBUG", message)

def info(message):
	_log("INFO", message)

def warn(message):
	_log("WARN", message)

def error(message):
	_log("ERROR", message)
