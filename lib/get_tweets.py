import requests
import numpy as np
import pandas as pd
import json
from IPython.display import display
import re
import os,sys,inspect
#currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
#parentdir = os.path.dirname(currentdir)
#sys.path.insert(0,parentdir)

from lib.twitter_keys import keys
import json
from twitter import Twitter, OAuth, TwitterHTTPError, TwitterStream


CONSUMER_KEY = keys['CONSUMER_KEY']
CONSUMER_SECRET = keys['CONSUMER_SECRET']
ACCESS_TOKEN = keys['ACCESS_TOKEN']
ACCESS_SECRET = keys['ACCESS_SECRET']

### -----------------------------------------------------------------------------------####
### geo bounding for tweet location----------------------------------------------------####

los_angeles = "-118.670883,33.733477,-117.695847,34.290126"
Santa_Monica = "-118.514757,33.980857,-118.417253,34.065264"
Dallas = "-96.904907,32.761906,-96.684917,33.080035"
Midland_Odessa = "-103.1575,31.4849,-101.5178,32.3591"
Sacramento_east = "-121.8658,38.445,-120.2618,39.3598"
SFO = "-122.5319,37.5751,-122.3438,37.824"

### -----------------------------------------------------------------------------------####
### connect to postgres----------------------------------------------------------------####

import psycopg2 as pg2
import psycopg2.extras as pgex
this_host='34.211.59.66'
this_user='postgres'
this_password='postgres'


### ------------------------------------------------------------------------------------####
### cleaning text ----------------------------------------------------------------------####

def cleaner(text):
    text = text.lower()
    text = re.sub("'","''", text)
    text = re.sub("{","\{",text)
    text = re.sub("}","\}",text)
    text = re.sub('\n',' ',text)

    #text = re.sub(":","\:",text)
    return text

### -------------------------------------------------------------------------------------####
### cleaning tweet ----------------------------------------------------------------------####

#from spacy.en import STOP_WORDS
#from spacy.en import English
#import nltk
#nlp = English()
def tweet_cleaner(text):
    text = text.lower()
    text = re.sub("'","''", text)
    text = re.sub("{","\{",text)
    text = re.sub("}","\}",text)
    text = re.sub(r'http\S+', '',text)
    text = re.sub(r'@\S+', '',text)
    
    text = re.sub('\s+',' ',text)
    text = re.sub('\n',' ',text) 
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)
    text = re.sub(emoji_pattern, '', text)    
#    text = ' '.join([i.lemma_ for i in nlp(text) 
#                   if i.orth_ not in STOP_WORDS])
    
    return text

### -----------------------------------------------------------------------------------####
### Collecting tweets------------------------------------------------------------------####



oauth = OAuth(ACCESS_TOKEN, ACCESS_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
twitter_stream = TwitterStream(auth=oauth)
#iterator = twitter_stream.statuses.filter(locations=Santa_Monica+','+\
#                                          Midland_Odessa+','+Dallas+','+\
#                                          Sacramento_east+','+SFO)
iterator = twitter_stream.statuses.filter(locations=los_angeles)
tweet_count = 300000

conn = pg2.connect(host = this_host, 
                        user = this_user,
                        password = this_password)


cur = conn.cursor()
for tweet in iterator:
    tweet_count -= 1  
   
    try:
        id_str = str(tweet['id_str'])
    except:    
        id_str = None
    try:
        screen_name = tweet['user']['screen_name']
    except:
        screen_name = None

    tweet_content = cleaner(tweet['text'])
    cleaned_tweet = tweet_cleaner(tweet['text'])
    screen_name = tweet['user']['screen_name']
    retweeted = tweet['retweeted']
    retweet_count = tweet['retweet_count']
    created_at = tweet['created_at']
    
    get_hashtags = lambda tweet: " ".join([i for i in tweet.split() if ('#' in i)])
    hashtags1 = get_hashtags(tweet_content)
    hashtags1 = re.sub('\W',' ',hashtags)
    hashtags1 = re.sub('\s+',' ',hashtags)
    if len(hashtags1) > 1:
        try: 
            hashtags = hashtags1
        except:
            hashtags = None
    try:
        location =  cleaner(tweet['place']['full_name'])
    except:
        location = None
    try:
        country = tweet['place']['country']
    except:
        country = None
    try:
        place_type = tweet['place']['place_type']
    except:
        place_type = None
    try:
        latitude = tweet["geo"]["coordinates"][0]
        longitude = tweet["geo"]["coordinates"][1]
    except:
        latitude = 0.0 
        longitude = 0.0  
    usr= tweet['user']
    lang = tweet['lang']
    try:
        time_zone = cleaner(tweet['user']['time_zone'])
    except:
        time_zone = None    
    sql_insert = '''insert into tweets 
                        (
                            id,
                            screen_name,
                            tweet_content,
                            cleaned_tweet,
                            hashtags,
                            created_at,
                            retweeted,
                            retweet_count,
                            location,
                            country,
                            place_type,
                            latitude,
                            longitude, 
                            time_zone,
                            lang
                        )
                    values
                        ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}');
                 '''.format(id_str,
                            screen_name,
                            tweet_content,
                            cleaned_tweet,
                            hashtags,
                            created_at,
                            retweeted,
                            retweet_count,
                            location,
                            country,
                            place_type,
                            latitude,
                            longitude,
                            time_zone,
                            lang
                           )
    print(str(tweet_count)+' '+ screen_name+ ':  '+ tweet_content)
    #print(latitude,longitude)
    cur.execute(sql_insert)
    conn.commit()    
    if tweet_count <= 0:
        break

conn.close()