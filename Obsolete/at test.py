import tweepy
import json
from datetime import datetime

tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication

#####Functions#####
def athenticate(tokenpath):
	token_file=open(tokenpath, 'r')
	tokens = json.load(token_file)
	token_file.close

	consumer_key = tokens[0]['consumer_key']
	consumer_secret = tokens[0]['consumer_secret']
	access_token = tokens[0]['access_token']
	access_token_secret = tokens[0]['access_token_secret']

	# Authenticate to Twitter API
	auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_token, access_token_secret)
	api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
	return api


api = athenticate(tokenpath)
searched_tweets = [status for status in tweepy.Cursor(api.search, q='#climateemergency', lang='en',tweet_mode='extended').items(100)]

#for tweet in searched_tweets:
#	print(tweet.full_text)
#	print('------------------------------------------------------\n')

print(len(searched_tweets))

id_list = [tweet.id for tweet in searched_tweets]
id_list.sort(reverse = False)
oldest_tweet = id_list[0]

for tweet in searched_tweets:
	if tweet.id == oldest_tweet:
		print(tweet.full_text)


print('Tweet creation time:',searched_tweets[0].created_at)

print('Time now:',datetime.now())

print('\n-----------\n')

fakedate = datetime.strptime('20190706 10:00:00', '%Y%m%d %H:%M:%S')
print('Fake time:',fakedate)

delta = fakedate-tweet.created_at

print('Delta days:',delta.days)
print('Delta:',delta)
print(type(delta))