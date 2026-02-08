from datetime import datetime
import sys

def log(message, is_error=False):
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	color_code = "\033[91m" if is_error else "\033[92m"
	reset_code = "\033[0m"
	
	formatted_message = f"[{timestamp}] {color_code}{message}{reset_code}"
	print(formatted_message, flush=True)

def info(message):
	log(message, is_error=False)

def error(message):
	log(message, is_error=True)
