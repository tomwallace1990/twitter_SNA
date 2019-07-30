#Sentiment checker
#Tom Wallace
#Created 03/07/2019
#Description: This script downloads tweets about a given user (sent @ them) and checks the sentiment, it can also check it for a specific topic or hashtag

#####Imports#####
import tweepy
import json
from datetime import datetime

#####Parameters and settings####
given_user='greenpeace'
topic_or_hashtag='#climateemergency'
allowRTs = False # Default false - if true it will process mostly the users own tweets (retweets count as mentions @given_user)
tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication

maxtweets=200
days_to_get=0

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

def gettext_extended(list_of_tweet_objects):
	tweettext=[]
	for tweet in list_of_tweet_objects:
		if 'RT @' in tweet.full_text: # IF they are RT get the non tructated
			try:
				tweet = 'RT @' + tweet.entities['user_mentions'][0]['screen_name'] + ': ' + tweet.retweeted_status.full_text
			except:
				tweet = tweet.full_text
		else:
			tweet = tweet.full_text
		tweettext.append(tweet)

	return tweettext

def tweetsatuser(api):
	if given_user.startswith('@') == False:
		query_str = '@' + given_user
	else:
		query_str = given_user
	if topic_or_hashtag !='':
		query_str = query_str + ' ' + topic_or_hashtag
	if allowRTs == False:
		query_str = query_str + '-filter:retweets'
	
	searched_tweets = [status for status in tweepy.Cursor(api.search, q=query_str, lang='en',tweet_mode='extended').items(maxtweets)]

	#Time limmiter
	if days_to_get !=0:
		dayscreatedago = [(datetime.now()-tweet.created_at).days for tweet in searched_tweets]
		searched_tweets = [tweet for tweet,time in zip(searched_tweets,dayscreatedago) if time <=days_to_get]

	return searched_tweets

def sentimentanalysis():


#####Main#####

api = athenticate(tokenpath)

searched_tweets = tweetsatuser(api)

print(len(searched_tweets))

tweet_text = gettext_extended(searched_tweets)

for each in tweet_text:
	print(each)

# = sentimentanalysis(tweet_text)