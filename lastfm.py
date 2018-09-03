import json
import urllib.request
import urllib.parse
from api import LASTFM_KEY

class FM:
	def __init__(self):
		self.key = LASTFM_KEY

	def search(self, method, params):
		url = f"http://ws.audioscrobbler.com/2.0/?method={method}&api_key={self.key}&format=json"
		for param, value in params.items():
			url = url + f"&{param}={value}"

		http = urllib.request.urlopen(url)
		return http.read()

	def get_artist(self, query):
		query = urllib.parse.quote(query)

		data = self.search(
			'artist.search',
			{
				'artist': query
			},
		)

		jdata = json.loads(data)['results']['artistmatches']['artist']

		if len(jdata) > 0:
			jdata = jdata[0]
			jdata['listeners'] = "{:,}".format(int(jdata['listeners']))
			return json.dumps(jdata)
		else:
			return False
