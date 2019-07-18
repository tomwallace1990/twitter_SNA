#Topic modeller
#Tom Wallace
#Created 20/06/2019
#Description: This finds topics a given user is tweeting about

#I could see how this could be tied into stuff Alerter does by showing how many recent tweets there are for each topic the script suggests.
# What are people saying about greenpeace 'about @handle'

#TODO

#Done
#	1. Add control for how many days to go back (as test for getting dates from tweets) - default to a week
#	2. Added a cursor to collect more than 200 tweets if requested

#####Imports#####
import tweepy
import json
import pickle
import re
import pandas as pd
import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
#nltk.download('stopwords') # this needs to be run the first time the script is run on a new machine, but then never again
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from datetime import datetime

#####Parameters and settings####
force_lower = False
no_of_tweets = 300 # Will collect this many and then filter by time based on 'days_to_get' below
days_to_get = 7 # Number of days to go back - default to 7 as that is the max than can be searched on the public API. set to 0 to disable time checking and get all tweets
results_to_print = 10 # Number of results to print from the top of the more used lists 
given_user='@netflix' # shell is good, british_airways? adidasUK? adidas?
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

def gettext_extended(list_of_tweet_objects):
	#This function gets the full text of a tweet, which is in a different place in the object depending of if it is a mention or retweet
	tweettext=[]
	for tweet in list_of_tweet_objects:
		if 'RT @' in tweet.full_text: # IF they are RT get the non tructated
			try:
				tweet = 'RT @' + tweet.entities['user_mentions'][0]['screen_name'] + ': ' + tweet.retweeted_status.full_text # Get the full retweeted text and then add the snipped RT @ bit back on
			except:
				tweet = tweet.full_text # For some reason a small numebr of retweets don't have the correct attributes, for them just get the truncated text
		else:
			tweet = tweet.full_text # Normal mentions give you the full text from full_text
		tweettext.append(tweet)

	return tweettext

def top_hashtags(tweets):
	#This funciton scans the tweets corpus for hashtags and counts them, printing the most commonly used in decendng order
	tweets = gettext_extended(tweets) # Replace the list of tweet objects with the full text

	if force_lower==True:
		tweets = list(map(lambda x :x.lower(), tweets)) # Somtimes hashtags are capitalised differently, force lower will make them all the same

	hashtags=[]
	for tweet in tweets:
		tags = re.findall('(?<=#)\w+', tweet) # Find the octothorpe followed by any single word i.e. a hashtag
		hashtags.append(tags) # Could be done with extend

	hashtags = [item for sublist in hashtags for item in sublist]

	count_dic={}
	for tag in hashtags:
		count = len(re.findall(tag,str(hashtags))) # Count how many of each hashtag there are and store it in a dictonary, this isn't an efficient method, but only working with a few hundred tweets 
		count_dic.update({tag:count})

	df = pd.DataFrame.from_dict(count_dic,orient='index', columns=['Count']) # Use a dataframe as an easy way to sort the list of hashtags by thier counts
	df.sort_values(by=['Count'], inplace=True, ascending=False)
	df.reset_index(inplace=True)
	index = list(df['index']) # Get the count and hashtags back as ordered lists
	Count = list(df['Count'])

	print('\nTop hashtags used by', given_user,'\n----------------------------') # Print the results
	counter=0
	for key,value in zip(index,Count):
		if value !=1:
			print('#',key,' used ', value, ' times.', sep='')
		else:
			print('#',key,' used ', value, ' time.', sep='')
		counter=counter+1
		if counter==results_to_print: # Only print requested amount from the top
			break

def topic(tweets):
	#This function impliments a basic topic model
	#https://ourcodingclub.github.io/2018/12/10/topic-modelling-python.html

	tweets = gettext_extended(tweets) # replace the list of objects with just the text
	tweets = list(map(lambda x :x.lower(), tweets)) # Topic modelling needs all in the same case, so this is no an option like in the hashtag function

	for each in ['http\S+','bit.ly/\S+','rt @\w+:', '#\w+','[^\w\d\s]','htt', '\d+']:
		tweets = list(map(lambda x :re.sub(each, '', x), tweets)) # Remove URLs, retweet codes, hashtags, things which aren't words, and numbers
	
	for each in ['\s\s+','\\n']: # replace any 2+ long white space or newlines with a single whitespace
		tweets = list(map(lambda x :re.sub(each, ' ', x), tweets))
	tweets = list(map(lambda x :x.strip(), tweets)) # Strip leading and following whitespace

	stopwords = nltk.corpus.stopwords.words('english') # Get stop words from the nltk library into a varaible
	stopwords.append('yes') # Add an additional stop word
	#word_rooter = nltk.stem.snowball.PorterStemmer(ignore_stopwords=False).stem

	tweet_token_list=[]
	for tweet in tweets:
		tweet = tweet.split(' ') # Split tweets into tokens of words on the whitespace
		tweet_token_list.append(tweet)

	tweet_token_list = [item for sublist in tweet_token_list for item in sublist if item not in stopwords] # check this

	#not needed
	#tweet_token_list = [word_rooter(word) for word in tweet_token_list]

	tweet_token_list = tweet_token_list+[tweet_token_list[i]+'_'+tweet_token_list[i+1] for i in range(len(tweet_token_list)-1)]
	#tweet = ' '.join(tweet_token_list)
	
	vectorizer = CountVectorizer(max_df=0.9, min_df=10, token_pattern='\w+|\$[\d\.]+|\S+')
	tf = vectorizer.fit_transform(tweet_token_list).toarray()
	tf_feature_names = vectorizer.get_feature_names() # this step may be good enough
	
	print('\nSuggested topics for', given_user.capitalize(), '\n----------------------------')
	counter=1
	for each in tf_feature_names:
		print(counter,'. ',each.capitalize(), sep='')
		counter=counter+1
		if counter==10:
			break

	#Below is the actual modelling but may not be needed
	"""
	number_of_topics = 3

	model = LatentDirichletAllocation(n_components=number_of_topics, random_state=0)

	model.fit(tf)

	def display_topics(model, feature_names, no_top_words):
		topic_dict = {}
		for topic_idx, topic in enumerate(model.components_):
			topic_dict["Topic %d words" % (topic_idx)]= ['{}'.format(feature_names[i])
							for i in topic.argsort()[:-no_top_words - 1:-1]]
			topic_dict["Topic %d weights" % (topic_idx)]= ['{:.1f}'.format(topic[i])
							for i in topic.argsort()[:-no_top_words - 1:-1]]
		return pd.DataFrame(topic_dict)

	no_top_words = 5
	topic_dict = display_topics(model, tf_feature_names, no_top_words)
	print(topic_dict)
	""" 

#####Main#####
api = athenticate(tokenpath)
tweets = [tweet for tweet in tweepy.Cursor(api.user_timeline, screen_name=given_user,tweet_mode='extended').items(no_of_tweets)] # Get the requested number of tweets from the requested users timeline
#tweets = [status for status in tweepy.Cursor(api.search, q='@'+given_user, lang='en',tweet_mode='extended').items(no_of_tweets)]
#This should be the same as the tweets from above, but @ the user rather than from the user

#pickle.dump(tweets, open( './TOPICtweets', 'wb'))
#tweets = pickle.load(open( './TOPICtweets', 'rb'))

#Time limmiter
if days_to_get !=0: # This will limmit the results to being from a set number of days ago, 0 means this function is disabled
	dayscreatedago = [(datetime.now()-tweet.created_at).days for tweet in tweets] # Work out how many days ago each tweet is from (as a simple int)
	tweets = [tweet for tweet,time in zip(tweets,dayscreatedago) if time <=days_to_get] # Modify the list of tweets to exclude those older than days_to_get

try:
	sincewhen = tweets[-1].created_at # Get the sending date of the oldest tweet
except:
	print('No tweets in given timefarame:', days_to_get, 'days.') # If all tweets have been filtered by the time limmiter then exit
	quit()

print('\nBased on ',len(tweets),' tweets sent by ',given_user, ' in the last ', (datetime.now()-tweets[-1].created_at).days, ' days, this script returns the top topics and hashtags the user is active in.', sep='')
print('These topics and hashtags may suggest networks the user is active in and may wish to search for.')
print('The oldest tweet was sent at:', sincewhen)

top_hashtags(tweets) # Get the top hashtags, printing is from whithin the function
#topic(tweets) # Get the top topics, printing is from whithin the function

