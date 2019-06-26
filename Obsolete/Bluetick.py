import json
import tweepy
import re
import pickle


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

def searchtwit(query, max_tweets, allowRTs):
	
	searched_tweets = [status for status in tweepy.Cursor(api.search, q=query, lang='en').items(max_tweets)]
	
	filteredlist=[]
	if allowRTs == False: # this version of the searchtwit function can filter out retweets if required
		for tweet_obj in searched_tweets: # for each tweet object in the list returned from the search
			if re.match('RT ', tweet_obj.text) is None: # re.match only searches from the front of the string, so no need to use a starting anchor ^
				filteredlist.append(tweet_obj) # make a list of non RTs
		searched_tweets = filteredlist # replace origional list with filtered list

	tweet_author = [tweet.user.screen_name for tweet in searched_tweets] # get a list of just the authors of each tweet
	tweet_text = [tweet.text for tweet in searched_tweets] # get a list of just the text of each tweet

	return tweet_author, tweet_text, searched_tweets

##############################

tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json'
api = athenticate(tokenpath) # auth

#user = api.get_user(screen_name='David_Cameron')

#print(user.screen_name, ':', user.verified)

max_tweets = 30
query = 'Extinction rebellion'
allowRTs = True



#account, corpus, searched_tweets = searchtwit(query, max_tweets, allowRTs)

#dump_data = zip(account, corpus, searched_tweets)
#pickle.dump(dump_data, open( './tweets', 'wb'))

dump_data = pickle.load(open( './tweets', 'rb'))
account, corpus, searched_tweets = zip(*dump_data)


tweet_num = 0
print('Retweets')
print(corpus[tweet_num])
print('Sender: ', searched_tweets[tweet_num].user.screen_name, ':', searched_tweets[tweet_num].user.verified) # can get the status of the sender, but not the mentioned accounts - if have to get the revicer list seperatly (inneficent but could cross check against the sender list first)
print('Reciver: ',searched_tweets[tweet_num].retweeted_status.user.screen_name, ':',searched_tweets[tweet_num].retweeted_status.user.verified)

print('\n')

print(searched_tweets[tweet_num])
