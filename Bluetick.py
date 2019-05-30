import json
import tweepy


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

def searchtwit(query, max_tweets):
	
	searched_tweets = [status for status in tweepy.Cursor(api.search, q=query, lang='en').items(max_tweets)]
	tweet_author = [tweet.user.screen_name for tweet in searched_tweets]
	tweet_text = [tweet.text for tweet in searched_tweets]

	return tweet_author, tweet_text, searched_tweets

##############################

tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json'
api = athenticate(tokenpath) # auth

user = api.get_user(screen_name='David_Cameron')

print(user.verified)

max_tweets = 3
query = 'Extinction rebellion'
account, corpus, searched_tweets = searchtwit(query, max_tweets)
print(searched_tweets[0].user.verified) # can get the status of the sender, but not the mentioned accounts - if have to get the revicer list seperatly (inneficent but could cross check against the sender list first)
