import requests
from log_util import error

def loganneRequest(data):
	data["source"] = "lucos_media_weightings"
	loganne_reponse = requests.post('https://loganne.l42.eu/events', json=data);
	if loganne_reponse.status_code != 202:
		error("Call to Loganne failed with "+str(loganne_reponse.status_code)+" response: " +  loganne_reponse.text)