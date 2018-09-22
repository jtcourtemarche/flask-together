#!/usr/bin/python

import requests
import json
import urllib.request
import urllib.error
import urllib.parse
from api import API_KEY

def check_channel_yt(url):
    api_url = "https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=date&channelId={0}&key={1}&part=id%2Csnippet".format(
        url.split('/channel/')[1],
        API_KEY
    )

    feed = urllib.request.urlopen(api_url).read()
    return json.loads(feed)['items']


def search_yt(query):
    query = str(urllib.parse.quote(query))
    url = "https://www.googleapis.com/youtube/v3/search?maxResults=20&type=video&order=relevance&q={0}&key={1}&part=id%2Csnippet".format(
        query,
        API_KEY
    )

    feed = urllib.request.urlopen(url).read()
    return json.loads(feed)['items']

# Tool that checks if valid youtube video

class Video():
    def __init__(self, items, contentDetails):
        if items and contentDetails:
            self.items = items
            self.contentDetails = contentDetails

    def get_items(self):
        return json.loads(self.items)['items'][0]

    def get_content(self):
        content = json.loads(self.contentDetails)['items'][0]
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

        duration = [int(d) for d in duration]
        # Convert to seconds
        duration = (duration[0] * 3600) + (duration[1] * 60) + duration[2]

        content['contentDetails']['duration'] = duration

        return content

def check_yt(id):
    feed = requests.get(f'https://www.googleapis.com/youtube/v3/videos?id={id}&key={API_KEY}&part=snippet').content
    content = requests.get(f'https://www.googleapis.com/youtube/v3/videos?id={id}&part=contentDetails&key={API_KEY}').content

    return Video(feed, content)