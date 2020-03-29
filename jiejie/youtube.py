#!/usr/bin/python
import json
from urllib.parse import quote
from collections import namedtuple

import requests

from config import YOUTUBE_KEY


# Returns JSON data for channel info query
def check_channel(url):
    api_url = 'https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=date&channelId={0}&key={1}&part=id%2Csnippet'.format(
        url.split('/channel/')[1],
        YOUTUBE_KEY
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
    url = f'https://www.googleapis.com/youtube/v3/search?maxResults={max_results}&type=video&order=relevance&q={query}&key={YOUTUBE_KEY}&part=id%2Csnippet'

    return requests.get(url).json()['items'][srange[0]:srange[1]]


# youtube video wrapper
class VideoWrapper:
    def __init__(self, video_id):
        self.watch_id, self.date, self.title, self.author, self.thumbnail, self.duration = self.get_metadata(video_id) 

    def __bool__(self):
        return bool(self.watch_id)

    def return_as_dict(self):
        return {
            'watch_id': self.watch_id,
            'date': self.date,
            'title': self.title,
            'author': self.author,
            'thumbnail': self.thumbnail,
            'duration': self.duration
        }

    def get_metadata(self, video_id):
        try:
            feed = requests.get(
                f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_KEY}&part=snippet').content
            content = requests.get(
                f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=contentDetails&key={YOUTUBE_KEY}').content
        except requests.exceptions.ConnectionError:
            # TODO: log that can't connect to API
            items, content = None, None
        else:
            items = json.loads(feed)['items'][0]
            duration = self.parse_duration(json.loads(content)['items'][0]) 

            return (
                items['id'],
                items['snippet']['publishedAt'],
                items['snippet']['title'],
                items['snippet']['channelTitle'],
                items['snippet']['thumbnails']['medium']['url'],
                duration
            )
        return (None, None, None, None, None, None) 

    def parse_duration(self, content):
        # TODO: refactor
        duration = content['contentDetails']['duration']

        # separate duration formats into array where ->
        #   [hours, minutes, seconds]

        # remove PT substring
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

        # convert to seconds
        return (duration[0] * 3600) + (duration[1] * 60) + duration[2]
