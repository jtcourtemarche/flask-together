#!/usr/bin/python
import json
from urllib.parse import quote

import requests

from api import API_KEY
from api import TWITCH_KEY


class TwitchAPI:
    def get_channel_data(channel):
        req = requests.get(
                'https://api.twitch.tv/helix/streams?first=1&user_login=' +
                channel, headers={'Client-ID': TWITCH_KEY}
        )
        try:
            return req.json()['data'][0]
        except IndexError:
            return False

    def get_channel_avatar(channel):
        req = requests.get('https://api.twitch.tv/helix/users?login=' +
                           channel, headers={'Client-ID': TWITCH_KEY})
        return req.json()['data'][0]['profile_image_url']


class YoutubeAPI:
    # Returns JSON data for channel info query
    def check_channel(url):
        api_url = 'https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=date&channelId={0}&key={1}&part=id%2Csnippet'.format(
            url.split('/channel/')[1],
            API_KEY
        )
        return requests.get(api_url).json()['items']

    # Returns JSON data for search query
    def search(query, srange):
        max_results = srange[1]

        # Max query size = 50
        if srange[0] > 50:
            return False
        elif srange[1] > 50:
            max_results = 50

        query = quote(query)
        url = f'https://www.googleapis.com/youtube/v3/search?maxResults={max_results}&type=video&order=relevance&q={query}&key={API_KEY}&part=id%2Csnippet'

        return requests.get(url).json()['items'][srange[0]:srange[1]]


# Youtube video object
class Video:
    def __init__(self, video_id):
        self.feed = requests.get(
            f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={API_KEY}&part=snippet').content
        self.content = requests.get(
            f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=contentDetails&key={API_KEY}').content

        items = json.loads(self.feed)['items'][0]

        self.id = items['id'],
        self.date = items['snippet']['publishedAt']
        self.title = items['snippet']['title']
        self.author = items['snippet']['channelTitle']
        self.thumbnail = items['snippet']['thumbnails']['medium']['url']

        self.content = self.get_content()

    def get_content(self):
        content = json.loads(self.content)['items'][0]
        duration = content['contentDetails']['duration']

        # Separate duration formats into array where ->
        #   [hours, minutes, seconds]

        # Remove PT
        duration = duration.replace('PT', '')

        if 'H' in duration:
            duration = [duration.split('H')[0], duration.split('H')[1]]
        else:
            duration = [0, duration.replace('H', '')]

        if 'M' in duration[1]:
            split_secondhand = duration[1].split('M')
            duration[1] = split_secondhand[0]
            duration.append(split_secondhand[1].replace('S', ''))
        else:
            duration.append(duration[1].replace('S', ''))
            duration[1] = 0

        if duration[2] == '':
            duration[2] = 0

        duration = [int(d) for d in duration]
        # Convert to seconds
        duration = (duration[0] * 3600) + (duration[1] * 60) + duration[2]

        content['contentDetails']['duration'] = duration

        return content
