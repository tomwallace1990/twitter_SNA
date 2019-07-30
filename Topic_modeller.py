#Topic modeller
#Tom Wallace
#Created 20/06/2019
#Description: This finds topics a given user is tweeting about or people are tweeting about a user. Using hashtags works better than topic modelling the text of the tweets.
#This script uses the public API, but as long as no_of_tweets is sensible (100-900) it isn't demanding on the API and runs quite quickly.
#The script could count hashtags for any collection of tweets, 

#Tasks done
#	0. Basic functionality - import tweets from user's timeline, count number of hashtags used in those tweets
#	1. Add control for how many days to go back (as test for getting dates from tweets) - default to a week
#	2. Added a cursor to collect more than 200 tweets if requested
#	3. What are people saying about greenpeace 'about @handle', this simply means making a different call in main and passing a different corpus to the functions

#####Imports#####
import tweepy
import json
import re
import pandas as pd
import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
#nltk.download('stopwords') # this needs to be run the first time the script is run on a new machine, but then never again
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from datetime import datetime
from textblob import TextBlob
import math

#####Parameters and settings####
tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication
force_lower = True # bool. if False hashtags with different capitalisation will be counted separately, if true they will be forced to lowercase and combined
no_of_tweets = 250 # int. Will collect this many and then filter by time based on 'days_to_get' below
days_to_get = 7 # int. Number of days to go back - default to 7 as that is the max than can be searched on the public API. set to 0 to disable time checking and get all tweets
results_to_print = 10 # int. Number of results to print from the top of the more used lists 
type_of_search = 'at' # cat. 'by' user or 'at' user
sentiment = True # bool. if true then perform sentiment analysis on the collected corpus. Uses the same functions as network analyser
given_user='@adidasUK' # string. Which user to search for shell, british_airways? adidasUK? adidas?

#####Functions#####
def athenticate(tokenpath):
	#Authenticate with the API and return an object which can call the API, this function is shared by other scripts
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
	#This function gets the full text of a tweet, which is in a different place in the object depending of if it is a mention or retweet. This function is used in other scripts.
	tweettext=[]
	for tweet in list_of_tweet_objects:
		if 'RT @' in tweet.full_text: # If the tweet is a RT then the full text is in 'retweeted_status.full_text'
			try:
				tweet = 'RT @' + tweet.entities['user_mentions'][0]['screen_name'] + ': ' + tweet.retweeted_status.full_text # Get the full retweeted text does not include the 'RT @user' so it's manually added back on here
			except:
				tweet = tweet.full_text # For some reason a small number of retweets don't have the correct attributes, for them just default to the truncated text
		else:
			tweet = tweet.full_text # Normal mentions give you the full text from the 'full_text' attribute
		tweettext.append(tweet) # construct a list of the text of each tweet

	return tweettext

def top_hashtags(tweets):
	#This function scans the tweets corpus for hashtags and counts them, printing the most commonly used in descending order
	#This can take any corpus of tweets and the input depends on what is fed to it by main
	tweets = gettext_extended(tweets) # Replace the list of tweet objects with the full text
	#If the script wasn't getting objects from the API then this line would need changed to accept the new input

	if force_lower==True:
		tweets = list(map(lambda x :x.lower(), tweets)) # Sometimes hashtags are capitalised differently, force lower will make them all the same

	hashtags=[]
	for tweet in tweets:
		tags = re.findall('(?<=#)\w+', tweet) # Find any octothorpe followed by any single word i.e. a hashtag
		hashtags.append(tags)

	hashtags = [item for sublist in hashtags for item in sublist] # some tweets have multiple hashtags so need to flatten the list

	count_dic={}
	for tag in hashtags:
		count = len(re.findall(tag,str(hashtags))) # Count how many of each hashtag there are and store it in a dictionary, this isn't an efficient method, but only working with a few hundred tweets 
		count_dic.update({tag:count})

	df = pd.DataFrame.from_dict(count_dic,orient='index', columns=['count']) # Use a dataframe as an easy way to sort the list of hashtags by their counts (as dictionaries are unordered)
	df.sort_values(by=['count'], inplace=True, ascending=False) # Sort tags by highest to lowest
	df.reset_index(inplace=True)
	hashtags = list(df['index']) # Get the count and hashtags back as ordered lists
	counts = list(df['count'])

	print('\nTop hashtags',type_of_search, given_user,'\n----------------------------') # Print the results
	counter=1
	if hashtags == []:
		print(given_user,'used no hashtags in this period.\n') # Quiet users may not have used any hashtags in the given period or number of tweets specified
	for tag,count in zip(hashtags,counts):
		if count !=1: # if the count is a plural use 'times'
			print(counter,'. #',tag,' used ', count, ' times.', sep='')
		else:
			print(counter,'. #',tag,' used ', count, ' time.', sep='')
		counter=counter+1
		if counter==results_to_print+1: # Only print requested amount from the top
			break

def topic(tweets):
	#This function implements a basic topic model. This doesn't seem very effective for tweets text, hashtag counting gives a better representation of topic.
	#https://ourcodingclub.github.io/2018/12/10/topic-modelling-python.html

	tweets = gettext_extended(tweets) # replace the list of objects with just the text
	tweets = list(map(lambda x :x.lower(), tweets)) # Topic modelling needs all in the same case, so this is no an option like in the hashtag function

	for each in ['http\S+','bit.ly/\S+','rt @\w+:', '#\w+','[^\w\d\s]','htt', '\d+']:
		tweets = list(map(lambda x :re.sub(each, '', x), tweets)) # Remove URLs, retweet codes, hashtags, things which aren't words, and numbers
	
	for each in ['\s\s+','\\n']: # replace any 2+ long white space or newlines with a single whitespace
		tweets = list(map(lambda x :re.sub(each, ' ', x), tweets))
	tweets = list(map(lambda x :x.strip(), tweets)) # Strip leading and following whitespace

	stopwords = nltk.corpus.stopwords.words('english') # Get stop words from the nltk library into a variable
	stopwords.append('yes') # Add an additional stop word
	#word_rooter = nltk.stem.snowball.PorterStemmer(ignore_stopwords=False).stem

	tweet_token_list=[]
	for tweet in tweets:
		tweet = tweet.split(' ') # Split tweets into tokens of words on the whitespace
		tweet_token_list.append(tweet)

	tweet_token_list = [item for sublist in tweet_token_list for item in sublist if item not in stopwords] # check this

	tweet_token_list = tweet_token_list+[tweet_token_list[i]+'_'+tweet_token_list[i+1] for i in range(len(tweet_token_list)-1)]
	
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

	#Below is the actual modelling but it over-processes, it is designed for large bodies of text rather than tweets
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

def sentiment_analysis(corpus, removedups=False):
	#This function calculates the average sentiment for a group of input tweets and returns an example tweet along side the average and number of tweets it was based on
	if removedups==True:
		corpus = removeduplicates(corpus) # Remove duplicates

	sentiment_scores=[]
	for tweet in corpus:
		tweet = re.sub('@\w+|^rt |[^a-z| ]|(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?','',tweet) # Remove urls, rt and non-english characters
		sentiment_scores.append(TextBlob(tweet).sentiment.polarity) # Get the sentiment scores from the TextBlob function
	
	#sentiment_scores_no_zero = [value for value in sentiment_scores if value !=0] # remove neutral sentiment
	ave_sentiment = sum(sentiment_scores)/float(len(sentiment_scores)) # Calculate the average
	ave_sentiment = float(str(ave_sentiment)[:4]) # Truncate the average
	number_of_tweets = len(corpus) # Calculate the n

	deviations = list(map(lambda x :abs(x-ave_sentiment), sentiment_scores)) # Calculate the deviation of each data point from the mean as an absolute value
	deviations_square = list(map(lambda x :x**2, deviations))
	sd = math.sqrt(sum(deviations_square)/len(deviations_square))
	sd = float(str(sd)[:4])

	dataframe_data = zip(sentiment_scores,corpus,deviations) # Add to df so can sort the lists and keep them ordered relitively
	df = pd.DataFrame(dataframe_data, columns=['score','tweet','deviations'])
	df.sort_values(by=['deviations'],ascending=True, inplace=True) # sort by deviations so 'average' tweets rise to the top
	example=list(df['tweet'])[0] # Get the first tweet of th ordered list - the closest to 'average' tweet

	return ave_sentiment, number_of_tweets, example, sd # return the average (float), number of tweets (int) and the example (string)

def english_sentiment(sentiment_score):
	#
	if sentiment_score <= -0.5:
		sentiment_in_english = 'very negative'
	elif sentiment_score > -0.5 and sentiment_score <= -0.3:
		sentiment_in_english = 'negative'
	elif sentiment_score > -0.3 and sentiment_score <= -0.1:
		sentiment_in_english = 'slightly negative'
	elif sentiment_score >-0.1 and sentiment_score <0.1:
		sentiment_in_english = 'neutral'
	elif sentiment_score >= 0.1 and sentiment_score < 0.3:
		sentiment_in_english = 'slightly positive'
	elif sentiment_score >= 0.3 and sentiment_score < 0.5:
		sentiment_in_english = 'positive'
	elif sentiment_score >= 0.5:
		sentiment_in_english = 'very positive'

	return sentiment_in_english

#####Main#####
api = athenticate(tokenpath) # authenticate with the API

if type_of_search=='by': # if want tweets by the user then just query their timeline
	tweets = [tweet for tweet in tweepy.Cursor(api.user_timeline, screen_name=given_user,tweet_mode='extended').items(no_of_tweets)] # Get tweets by the user
elif type_of_search=='at': # if want tweets about then make a general API query with '@user' 
	tweets = [status for status in tweepy.Cursor(api.search, q='@'+given_user, lang='en',tweet_mode='extended').items(no_of_tweets)] # Get tweets about the user
else:
	print("Type_of_search variable set wrong, try 'by' or 'at'")
	quit()

#Time limiter
if days_to_get !=0: # This will limit the results to being from a set number of days ago, 0 means this function is disabled
	dayscreatedago = [(datetime.now()-tweet.created_at).days for tweet in tweets] # Work out how many days ago each tweet is from (as a simple int)
	tweets = [tweet for tweet,time in zip(tweets,dayscreatedago) if time <=days_to_get] # Modify the list of tweets to exclude those older than days_to_get

try:
	sincewhen = tweets[-1].created_at # Get the sending date of the oldest tweet for the users info
except:
	print('No tweets in given time-frame:', days_to_get, 'days.') # If all tweets have been filtered by the time limiter then exit
	print("Try disabling 'days_to_get' by setting it to 0.")
	quit()

print('\nBased on ',len(tweets),' tweets ',type_of_search,' ',given_user, ' in the last ', (datetime.now()-tweets[-1].created_at).days, ' days, this script returns the top hashtags in the corpus.', sep='')
print('These topics and hashtags may suggest networks the user is active in and may wish to search for.')
print('The oldest tweet was sent at:', sincewhen)

top_hashtags(tweets) # Get the top hashtags, printing is from within the function
#topic(tweets) # Get the top topics, printing is from within the function. Disabled as hashtags work far better for tweets.
if sentiment == True:
	tweets = gettext_extended(tweets)
	sentiment, number_of_tweets, example, sd = sentiment_analysis(tweets)
	print('\nThe sentiment for this corpus of tweets is:',sentiment, 'with a polarity of', sd)
	print('This indicates', english_sentiment(sentiment),'sentiment.')