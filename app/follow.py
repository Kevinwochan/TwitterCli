import os
from time import sleep
from datetime import datetime
from random import randint
import re
import json
import pickle
import urllib
import logging
import argparse
import requests
from tabulate import tabulate
from config import TWEETS_SAVE_FILE, MAX_RETRIES
'''
Globals
'''
WELCOME_TEXT = r'''
|  \    /  \                                  |  \                          |  \      |  \
 \$$\  /  $$______   __    __         _______ | $$____    ______   __    __ | $$  ____| $$
  \$$\/  $$/      \ |  \  |  \       /       \| $$    \  /      \ |  \  |  \| $$ /      $$
   \$$  $$|  $$$$$$\| $$  | $$      |  $$$$$$$| $$$$$$$\|  $$$$$$\| $$  | $$| $$|  $$$$$$$
    \$$$$ | $$  | $$| $$  | $$       \$$    \ | $$  | $$| $$  | $$| $$  | $$| $$| $$  | $$
    | $$  | $$__/ $$| $$__/ $$       _\$$$$$$\| $$  | $$| $$__/ $$| $$__/ $$| $$| $$__| $$
    | $$   \$$    $$ \$$    $$      |       $$| $$  | $$ \$$    $$ \$$    $$| $$ \$$    $$
     \$$    \$$$$$$   \$$$$$$        \$$$$$$$  \$$   \$$  \$$$$$$   \$$$$$$  \$$  \$$$$$$$
 __        __                            __        __               
|  \      |  \                          |  \      |  \              
| $$____   \$$  ______    ______        | $$____   \$$ ______ ____  
| $$    \ |  \ /      \  /      \       | $$    \ |  \|      \    \ 
| $$$$$$$\| $$|  $$$$$$\|  $$$$$$\      | $$$$$$$\| $$| $$$$$$\$$$$\
| $$  | $$| $$| $$   \$$| $$    $$      | $$  | $$| $$| $$ | $$ | $$
| $$  | $$| $$| $$      | $$$$$$$$      | $$  | $$| $$| $$ | $$ | $$
| $$  | $$| $$| $$       \$$     \      | $$  | $$| $$| $$ | $$ | $$
 \$$   \$$ \$$ \$$        \$$$$$$$       \$$   \$$ \$$ \$$  \$$  \$$

'''

HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0',
    'authorization':
    'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
    "x-guest-token": "",
}


class Tweet():
    '''
    Data model for a tweet
    '''
    def __init__(self, id, time, message, twitter_handle):
        self.id = id
        self.time = time
        self.message = message
        self.handle = twitter_handle

    def __str__(self):
        table = "\n" + tabulate([[
            self.handle, self.time,
            f'https://twitter.com/{self.handle}/status/{self.id}'
        ]],
                                headers=['Twitter Handle', 'Time', 'URL'],
                                tablefmt="grid")
        table += "\n\"" + self.message + "\"\n\n"
        return table

    def __iter__(self):
        yield 'id', self.id
        yield 'time', self.time
        yield 'message', self.message
        yield 'handle', self.handle


class TwitterApiParser():
    def __init__(self):
        self.users = {}

    def parse_tweets(self, tweets_json, twitter_handle):
        '''
        Converts the json from a search response to a list of Tweets
        '''
        try:
            tweets_json = tweets_json['globalObjects']['tweets']
        except:
            logging.critical(
                f'API structure for tweets appears to have changed, exiting...'
            )
            exit(1)

        tweets = []
        for tweet_id, tweet in tweets_json.items():
            try:
                if tweet['user_id_str'] not in self.users:
                    continue  # Skip quoted tweets that appear in the reponse
                time = datetime.strptime(tweet['created_at'],
                                         '%a %b %d %H:%M:%S %z %Y')
                message = tweet['full_text']
                new_tweet = Tweet(tweet_id, time, message, twitter_handle)
                tweets.append(new_tweet)
            except:
                logging.critical(
                    f'API structure for a tweet appears to have changed, exiting...'
                )
                exit(1)
        tweets.sort(key=lambda tweet: tweet.time.timestamp())
        return tweets

    def load_user(self, twitter_handle, user_json):
        '''
        Stores the twitter_handle to user_id mapping
        Tweets made by loaded users are the only tweets that are printed/saved
        '''
        try:
            user_id = user_json['data']['user']['rest_id']
        except:
            logging.critical(
                f'API structure for users appears to have changed, exiting...')
            exit(1)
        self.users[user_id] = twitter_handle


class Twitter():
    def __init__(self):
        self.session = requests.Session()
        self.parser = TwitterApiParser()
        self.failed_requests = 0

    def create_session(self):
        '''
        Returns a guest session initialised by Twitter
        '''
        global HEADERS
        response = self.session.get("https://twitter.com/")
        try:
            new_guest_token = re.search(r'\("gt=(\d+);', response.text)[1]
        except:
            logging.fatal(f'guest token could not be retrieved')
        logging.debug(f'guest token generated')
        HEADERS['x-guest-token'] = new_guest_token
        return

    def map_user_id(self, twitter_handle):
        '''
        Stores the mapping of handle to user ID in the parser
        '''
        try:
            response = self.session.get(
                f'https://twitter.com/i/api/graphql/jMaTS-_Ea8vh9rpKggJbCQ/UserByScreenName',
                params={
                    'variables':
                    json.dumps({
                        "screen_name": twitter_handle,
                        "withHighlightedLabel": True  # Required
                    }),
                },
                headers=HEADERS)
        except:
            logging.warn(
                f'failed to retrieve user_id for {twitter_handle}: FAILURE #{self.failed_requests}'
            )
            self.failed_requests += 1
            return

        logging.debug(f'User mapping request made {response.status_code}')
        self.parser.load_user(twitter_handle, response.json())
        return

    def fetch_latest_tweets(self, twitter_handle, num_tweets=5):
        '''
        Fetches the tweets the API provides for a given twitter handle
        '''
        tweets = []
        try:
            response = self.session.get(
                'https://api.twitter.com/2/search/adaptive.json',
                params={
                    'count': num_tweets,
                    'q':
                    f'from:{twitter_handle} -filter:replies',  # filter out replies and only from twitter handle
                    'tweet_mode': 'extended',  # do not truncate
                    'tweet_search_mode': 'live',  # latest tweets
                },
                headers=HEADERS)
        except:
            logging.warn(
                f'failed to fetch the most {num_tweets} recent tweets for {twitter_handle}, received {response.status_code}, FAILURE:#{self.failed_requests}'
            )
            self.failed_requests += 1
            return tweets

        logging.debug(f'fetched latest tweets {response.status_code}')
        tweets = self.parser.parse_tweets(response.json(), twitter_handle)
        return tweets

    def fetch_tweets_since(self, twitter_handle, timestamp):
        '''
        Fetches the tweets the API provides for a given twitter handle
        '''
        tweets = []
        try:
            response = self.session.get(
                'https://api.twitter.com/2/search/adaptive.json',
                params={
                    'q':
                    f'from:{twitter_handle} -filter:replies since:{timestamp}',
                    'tweet_mode': 'extended',
                    'tweet_search_mode': 'live',
                },
                headers=HEADERS)
        except:
            logging.warn(
                f'failed to fetch tweets since {timestamp} for {twitter_handle}, received {response.status_code}, FAILURE:#{self.failed_requests}'
            )
            self.failed_requests += 1
            if self.failed_requests > 20:
                exit(1)
            return tweets

        logging.debug(
            f'fetched tweets since {timestamp} {response.status_code}')

        tweets = self.parser.parse_tweets(response.json(), twitter_handle)

        return tweets


'''
Initialising
'''
#logging.basicConfig(filename='follower.log', filemode='w', level=logging.INFO)
logging.basicConfig(level=logging.INFO)
logging.info(WELCOME_TEXT)
LAST_TWEET = datetime.now()

parser = argparse.ArgumentParser(
    description='Displays a twitter user\'s tweets')
parser.add_argument('--user',
                    type=str,
                    help='the users\'s twitter handle without @. E.g thegrugq')
args = parser.parse_args()
USER = os.getenv('USER', args.user)

if USER == None:
    logging.critical(
        f'Please set the Environment Variable USER when using the docker')
    logging.critical(
        f'E.g docker run --rm --name api -p 80:80 kevinwochan -e USER=thegrugq'
    )
    exit(1)
'''
Core Logic
'''
twitter_client = Twitter()
twitter_client.create_session()
twitter_client.map_user_id(USER)
tweets = twitter_client.fetch_latest_tweets(USER, 5)
if len(tweets) > 0:
    LAST_TWEET = tweets[-1]

for tweet in tweets:
    logging.info(tweet)

for tweet in tweets:
    pickle.dump(dict(tweet), open(TWEETS_SAVE_FILE, 'ab'))

while True:
    # sleep(10 * 60)  # 10 Minutes
    sleep(10 + randint(0, 5))  # randomisation should be used to diguise activity
    logging.info('#### Checking for new tweets ####')
    tweets = twitter_client.fetch_tweets_since(
        USER, int(LAST_TWEET.time.timestamp()))

    tweets = list(filter(lambda tweet: tweet.id != LAST_TWEET.id, tweets))

    if len(tweets) == 0:
        logging.info(f'#### No new tweets since {LAST_TWEET.time} ####')
        continue

    for tweet in tweets:
        logging.info(tweet)
    LAST_TWEET = tweets[-1]

    for tweet in tweets:
        pickle.dump(dict(tweet), open(TWEETS_SAVE_FILE, 'ab'))
