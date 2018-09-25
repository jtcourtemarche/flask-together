import json
import time
import requests
import hashlib
import urllib.request
import urllib.parse
from api import LASTFM_KEY, LASTFM_SECRET
from extensions import pipe


class FM:
    def __init__(self):
        self.key = LASTFM_KEY

    def search(self, method, params):
        url = f"http://ws.audioscrobbler.com/2.0/?method={method}&api_key={self.key}&format=json"
        for param, value in params.items():
            url = url + f"&{param}={value}"

        http = urllib.request.urlopen(url)
        return http.read()

    def get_user(self, name):
        data = self.search(
            'user.getInfo',
            {
                'user': name,
            }
        )

        return json.loads(data)

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

    def sign_call(self, args):
        # Construct hash string
        string = ""
        for key, value in sorted(args.items()):
            string += key
            string += value

        string += LASTFM_SECRET

        md5hash = hashlib.md5(string.encode('utf-8'))
        return md5hash.hexdigest()

    def get_session(self, token):
        api_sig = self.sign_call({'api_key': LASTFM_KEY, 'method': 'auth.getSession', 'token': token})

        content = requests.get(
            f'http://ws.audioscrobbler.com/2.0/?method=auth.getSession&api_key={LASTFM_KEY}&token={token}&format=json&api_sig={api_sig}'
        ).content

        session = json.loads(content)

        # Failed to get session
        if 'error' in session:
            return (False, session)

        return (True, session['session'])

    def scrobble(self, username):
        pdata = pipe.get(username).execute()[0]
        fmdata = json.loads(pdata)

        time_prior = time.time() - float(fmdata['timestamp'])

        if time_prior > 240 or (time_prior / fmdata['duration']) > 0.5:
            api_sig = self.sign_call({
                'method': 'track.scrobble',
                'api_key': LASTFM_KEY,
                'artist': fmdata['artist'],
                'track': fmdata['track'],
                'sk': fmdata['sk'],
                'timestamp': str(fmdata['timestamp']),
            })

            resp = requests.post('http://ws.audioscrobbler.com/2.0/', data={
                'method': 'track.scrobble',
                'api_key': LASTFM_KEY,
                'format': 'json',
                'api_sig': api_sig,
                'artist': fmdata['artist'],
                'track': fmdata['track'],
                'sk': fmdata['sk'],
                'timestamp': fmdata['timestamp']
            })

            if resp.status_code == 200:
                return True
        return False


    def update_now_playing(self, artist, track, user, duration):
        sk = user.fm_sk

        if duration > 30:
            # Check if duration over 30s
            api_sig = self.sign_call({
                'method': 'track.updateNowPlaying',
                'api_key': LASTFM_KEY,
                'artist': artist,
                'track': track,
                'sk': user.fm_sk,
            })

            resp = requests.post('http://ws.audioscrobbler.com/2.0/', data={
                'method': 'track.updateNowPlaying',
                'api_key': LASTFM_KEY,
                'format': 'json',
                'api_sig': api_sig,
                'artist': artist,
                'track': track,
                'sk': user.fm_sk,
            })

            if resp.status_code == 200:
                # Cache scrobble in redis
                pipe_data = {
                    'artist': artist,
                    'track': track,
                    'sk': user.fm_sk,
                    'timestamp': time.time(),
                    'duration': duration,
                }
                pipe_data = json.dumps(pipe_data)
                pipe.set(user.username, pipe_data)

        else:
            # Video does not meet requirements to be scrobbled
            pipe.set(user.username, '')

        pipe.execute()
