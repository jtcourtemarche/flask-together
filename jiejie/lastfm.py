import hashlib
import json
import time
from urllib.parse import quote

import requests

from api import LASTFM_KEY
from api import LASTFM_SECRET
from extensions import pipe


class FM:
    def __init__(self):
        self.key = LASTFM_KEY

    # General API call method
    def call(self, method, params):
        url = f'http://ws.audioscrobbler.com/2.0/?method={method}&api_key={self.key}&format=json'
        for param, value in params.items():
            url = url + f'&{param}={value}'

        http = requests.get(url)
        return http.json()

    # Get data of specific LastFM user

    def get_user(self, name):
        data = self.call(
            'user.getInfo',
            {'user': name}
        )

        # Format user's play count with commas
        data['user']['playcount'] = ('{:,}').format(data['user']['playcount'])
        return data

    # Get data on artist

    def get_artist(self, query):
        # Format user query to URL
        query = quote(query)

        # Get artist data from LastFM API
        data = self.call(
            'artist.search',
            {'artist': query},
        )

        # Get artist tags from LastFM API
        artist_tags = self.call(
            'artist.getTopTags',
            {'artist': query},
        )
        tags = artist_tags['toptags']['tag']
        tags = [tag['name'] for tag in tags]

        # Convert LastFM response from JSON to dict()
        jdata = data['results']['artistmatches']['artist']
        jdata[0]['tags'] = ', '.join(tags[:4])

        # Validate response
        if len(jdata) > 0:
            jdata = jdata[0]
            jdata['listeners'] = '{:,}'.format(int(jdata['listeners']))
            return json.dumps(jdata)
        else:
            return False

    # Construct an md5 hash string to sign API calls
    #   -> args is a dictionary of parameters and values to pass to API in URL

    def sign_call(self, args):
        string = ''
        for key, value in sorted(args.items()):
            string += key
            string += value

        string += LASTFM_SECRET

        md5hash = hashlib.md5(string.encode('utf-8'))
        return md5hash.hexdigest()

    # Get LastFM session key

    def get_session(self, token):
        api_sig = self.sign_call(
            {'api_key': LASTFM_KEY, 'method': 'auth.getSession', 'token': token})

        session = requests.get(
            f'http://ws.audioscrobbler.com/2.0/?method=auth.getSession&api_key={LASTFM_KEY}&token={token}&format=json&api_sig={api_sig}'
        ).json()

        # Failed to get session
        if 'error' in session:
            return False, session

        return True, session['session']

    # Pushes scrobble to LastFM

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

    # Lists song as 'Now Playing' on LastFM.
    # Caches currently playing song if available.
    # When another video is played, if requirements are met,
    # the cached data will be passed to the scrobble() method

    def update_now_playing(self, artist, track, user, duration):
        # Check if duration over 30s
        if duration >= 30:
            # Sign track.updateNowPlaying
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
