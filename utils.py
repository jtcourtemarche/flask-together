#!/usr/bin/python

import json
import urllib.request
import urllib.error
import urllib.parse
from api import API_KEY

# Youtube API Tools


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


def check_yt(id):
    url = "https://www.googleapis.com/youtube/v3/videos?id={0}&key={1}&part=snippet".format(
        id, API_KEY)
    feed = urllib.request.urlopen(url).read()
    if feed:
        return json.loads(feed)

    else:
        return False
