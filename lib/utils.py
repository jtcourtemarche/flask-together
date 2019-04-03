#!/usr/bin/python

import requests
import json
from urllib.parse import quote
from api import API_KEY


def check_channel_yt(url):
    api_url = "https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=date&channelId={0}&key={1}&part=id%2Csnippet".format(
        url.split('/channel/')[1],
        API_KEY
    )

    feed = requests.get(api_url).json()
    return feed['items']


def search_yt(query, srange):
    max_results = srange[1]

    # Max query size = 50
    if srange[0] > 50:
        return False
    elif srange[1] > 50:
        max_results = 50

    query = quote(query)
    url = f"https://www.googleapis.com/youtube/v3/search?maxResults={max_results}&type=video&order=relevance&q={query}&key={API_KEY}&part=id%2Csnippet"
    
    feed = requests.get(url).json()
   
    return feed['items'][srange[0]:srange[1]]


# Youtube video object
class Video:
    def __init__(self, video_id):
        self.feed = requests.get(f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={API_KEY}&part=snippet').content
        self.content = requests.get(f'https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=contentDetails&key={API_KEY}').content

        items = json.loads(self.feed)['items'][0]

        self.id = items['id'],
        self.date = items['snippet']['publishedAt']
        self.title = items['snippet']['title']
        self.author = items['snippet']['channelTitle']
        self.thumbnail = items['snippet']['thumbnails']['default']['url']

        self.content = self.get_content()

    def get_content(self):
        content = json.loads(self.content)['items'][0]
        duration = content['contentDetails']['duration']

        # Separate duration format into array where ->
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

