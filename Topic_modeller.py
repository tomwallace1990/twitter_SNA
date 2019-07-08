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
#nltk.download('stopwords')
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from datetime import datetime

#####Parameters and settings####
force_lower = False
no_of_tweets = 300 # Will collect this many and then filter by time based on 'days_to_get' below
days_to_get = 7 # number of days to go back - default to 7 as that is the max than can be searched on the public API. set to 0 to disable time checking and get all tweets
given_user='greenpeace'
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

def top_hashtags(tweets):

	tweets = gettext_extended(tweets)

	#tweets = list(map(lambda x :x.full_text, tweets)) # this gets some truncated if they are RT
	if force_lower==True:
		tweets = list(map(lambda x :x.lower(), tweets))

	hashtags=[]
	for tweet in tweets:
		tags = re.findall('(?<=#)\w+', tweet)
		hashtags.append(tags)

	hashtags = [item for sublist in hashtags for item in sublist]

	count_dic={}
	for tag in hashtags:
		count = len(re.findall(tag,str(hashtags)))
		count_dic.update({tag:count})

	df = pd.DataFrame.from_dict(count_dic,orient='index', columns=['Count'])

	df.sort_values(by=['Count'], inplace=True, ascending=False)
	df.reset_index(inplace=True)

	index = list(df['index'])
	Count = list(df['Count'])

	print('\nTop hashtags used by', given_user,'\n----------------------------')
	counter=1
	for key,value in zip(index,Count):
		if value !=1:
			print('#',key,' used ', value, ' times.', sep='')
		else:
			print('#',key,' used ', value, ' time.', sep='')
		counter=counter+1
		if counter==11:
			break

def topic(tweets):
	#https://ourcodingclub.github.io/2018/12/10/topic-modelling-python.html

	tweets = gettext_extended(tweets)
	tweets = list(map(lambda x :x.lower(), tweets))

	for each in ['http\S+','bit.ly/\S+','rt @\w+:', '#\w+','[^\w\d\s]','htt', '\d+']:
		tweets = list(map(lambda x :re.sub(each, '', x), tweets))
	
	for each in ['\s\s+','\\n']:
		tweets = list(map(lambda x :re.sub(each, ' ', x), tweets))
		tweets = list(map(lambda x :re.sub(each, ' ', x), tweets))
	tweets = list(map(lambda x :x.strip(), tweets))

	stopwords = nltk.corpus.stopwords.words('english')
	stopwords.append('yes')
	word_rooter = nltk.stem.snowball.PorterStemmer(ignore_stopwords=False).stem

	tweet_token_list=[]
	for tweet in tweets:
		tweet = tweet.split(' ')
		tweet_token_list.append(tweet)

	tweet_token_list = [item for sublist in tweet_token_list for item in sublist if item not in stopwords]

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
tweets = [tweet for tweet in tweepy.Cursor(api.user_timeline, screen_name=given_user,tweet_mode='extended').items(no_of_tweets)]

#pickle.dump(tweets, open( './TOPICtweets', 'wb'))
#tweets = pickle.load(open( './TOPICtweets', 'rb'))

#Time limmiter
if days_to_get !=0:
	dayscreatedago = [(datetime.now()-tweet.created_at).days for tweet in tweets]
	tweets = [tweet for tweet,time in zip(tweets,dayscreatedago) if time <=days_to_get]

sincewhen = tweets[-1].created_at
print('\nBased on ',len(tweets),' tweets sent by ',given_user, ' in the last ', (datetime.now()-tweets[-1].created_at).days, ' days, this script returns the top topics and hashtags the user is active in.', sep='')
print('These topics and hashtags may suggest networks the user is active in and may wish to search for.')
print('The oldest tweet was sent at:', sincewhen)

top_hashtags(tweets)
topic(tweets)

