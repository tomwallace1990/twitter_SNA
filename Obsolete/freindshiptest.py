import tweepy
import json
import re
import pandas as pd
import pickle

tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication

query = 'extinction rebellion'

def athenticate(tokenpath):
	#This simply authenticates with the API and returns an API wrapper object. Stored in a function as it is sometimes called to re-authenticate if there is an error.	
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

result = api.show_friendship(source_screen_name='verified', target_screen_name='martindaubney')
print(result) 
#faurecia genuinly not followed, so the list is incomplete
#martindaubney is followed but not in JSON? not in the initial ID list - is is new IDlist
#brexithenrik is followed but not in JSON not in the initial ID list - is in new IDlist
#netpol is followed but not in JSON  -recently changed handle, will need to design rolling to accout for that
#abcnews - not followed by verified
#financialtimes - not followed by verifed

"""

result = api.show_friendship(source_screen_name='verified', target_screen_name='shell')
print(result)

userinfo = api.get_user(screen_name='financialtimes')
print(userinfo.screen_name, userinfo.verified, userinfo.id)

userinfo = api.get_user(id='2768501')
print(userinfo.screen_name, userinfo.verified)


valid_ids_list = pickle.load(open('./Data/Valid_twitter_handles/validIDs', 'rb'))

print(type(valid_ids_list[0]))

if  2768501 in valid_ids_list:
	print('True')

print('\n')

valid_ids_list_old = pickle.load(open('./Data/Valid_twitter_handles/Fristrun/validIDs', 'rb'))

print(len(valid_ids_list))
print(len(valid_ids_list_old))

print(valid_ids_list[0])

userinfo = api.get_user(screen_name='verified')
print(userinfo.screen_name, userinfo.friends_count)

"""

valid_ids_list_dups = pickle.load(open('./Data/Valid_twitter_handles/validIDs180719-withdups', 'rb'))
valid_ids_list_top100 = pickle.load(open('./Data/Valid_twitter_handles/validIDs', 'rb'))

print(len(valid_ids_list_dups))
print(len(valid_ids_list_top100))

for each in valid_ids_list_top100:
	if each not in valid_ids_list_dups:
		valid_ids_list_dups.append(each)

print(len(valid_ids_list_dups))

#something lile...
while length of set not (variable from api.freinds):
	download validIDs
	and keep doing it until its right
#work out how its actually missing stuff
quit()

######################################################

def validate(valid_dict, all_handles):
	with open('./valid_screennames.json') as json_file:  
	    valid_screen_names = json.load(json_file)
	    validlist = [each.lower() for each in valid_screen_names.values()]

	for handle in all_handles:
		if handle.lower() in validlist:
			valid_dict.update({handle.lower() : True})
		else:
			valid_dict.update({handle.lower() : False})

	return valid_dict

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

def searchtwit(max_tweets, allowRTs,get_user_activity):
	print('Searching twitter for ', max_tweets, ' tweets about "', query, '". Please wait...', sep='')
	if allowRTs == False:
		search_query = query + '-filter:retweets' # This string can be appended onto a query to prevent the API returning retweets - this is much more efficiant than filtering post-search
	else:
		search_query = query
	searched_tweets = [status for status in tweepy.Cursor(api.search, q=search_query, lang='en',tweet_mode='extended').items(max_tweets)]

	tweet_author = [tweet.user.screen_name for tweet in searched_tweets] # get a list of just the authors of each tweet
	#tweet_text = [tweet.text for tweet in searched_tweets] # get a list of just the text of each tweet

	tweet_text = gettext_extended(searched_tweets)
	
	if get_user_activity == True: # get tweets from users timeline and append to the end of the authors, text, and object list
		id_list = [tweet.id for tweet in searched_tweets]
		id_list.sort(reverse = False)
		oldest_tweet = id_list[0] 
		tweet_author, tweet_text, searched_tweets = getusertweets(tweet_author, tweet_text, searched_tweets, oldest_tweet)

	return tweet_author, tweet_text, searched_tweets

def edgelister(authors, tweets, selfloop=False, removedups=True, sav_path=None): 
	# This function takes tweet objects and generates an edgelist, which is a pair of equal length lists showing the sender and receiver of each tweet which contains one or more '@'
	# Where there is more than one '@' in a tweet an equal number of lines is created in the edge list
	# This function expects a list of string handles and a matching list of tweet text.
	# Example: the tweet 'hi, this is a test @test @testing' by account tomw would result in the lists - [tomw, tomw] [test, testing] 

	sender, receiver=[], []

	for tweet, author in zip(tweets, authors): # Need to do a zip loop to keep author linked to the right tweet
		links = re.findall(r'(?<=@)\w+', tweet) # Use regex to find the block of characters folliwng the @ symbol which is the receiving handle
		if len(links) > 0: # This checks if an @ was actually found, if not it moves back to the start of the loop
			for link in links: # There is often more than one @ in a tweet, this ensures they are all captured
				sender.append(author) # The sender is the author of the tweet
				receiver.append(link) # The receiver is each handle after the @
		if selfloop == True and len(links) == 0:
			sender.append(author)
			receiver.append(author)
	
	if len(sender) == len(receiver): # The lists should always been the same length, if not something has gone wrong
		if sav_path != None: # If i save path is supplied then convert the lists into a dataframe and save them as a CSV - this is an efficent way of storing network data
			outputdict = {'Sender': sender, 'Receiver': receiver}
			df_out = pd.DataFrame(outputdict)
			df_out.to_csv(sav_path)
			print('Edge list saved at:', sav_path)
		return sender, receiver # Return the edgelist
	else:
		print('>>> WARN: Mismatch error <<<')
		quit() # If something is wrong warn the user and exit

#Authenticate via public API
api = athenticate(tokenpath)

#NEW
max_tweets=2000
allowRTs = True
get_user_activity=False
selfloop=False
removedups=False

#Grab tweets on given topic from API. Account is list of senders, corpus is matching list of tweet text, searched_tweets is matching list of the full tweet objects
account, corpus, searched_tweets = searchtwit(max_tweets, allowRTs,get_user_activity)

#Case conversion
account = [text.lower() for text in account]
corpus = [text.lower() for text in corpus]

#Create edge list
sender, receiver = edgelister(account, corpus, selfloop, removedups)

valid_dict_new = {}
all_handles = (list(set(sender+receiver)))
valid_dict_new = validate(valid_dict_new, all_handles)

#for key,value in valid_dict_new.items():
#	if value == True:
#		print(key)

#OLD
def prevalidate (valid_dict, searched_tweets):

	for tweet in searched_tweets:
		valid_dict.update({tweet.user.screen_name.lower() : tweet.user.verified})
		try:
			if re.match('RT @', tweet.text) is not None:
				valid_dict.update({tweet.retweeted_status.user.screen_name.lower() : tweet.retweeted_status.user.verified})
		except:
			pass
	return valid_dict

def primevalidate (users, valid_dict):

	print('Making API calls for ', len(users), ' users. Please wait...', sep='')
	for user in users:
		try:
			userinfo = api.get_user(screen_name=user)	
			valid_dict.update({userinfo.screen_name.lower() : userinfo.verified})
		except:
			valid_dict.update({user : None})
	return valid_dict


valid_dict = {}
valid_dict = prevalidate(valid_dict, searched_tweets)

#Validation - primevalidate (get remaining users status from API)
	#This gets the accounts not captured during prevalidation - each account requires an API call so this is inefficent
dict_list = list(valid_dict.keys()) # Get a list of what's we already have validation info for

unverified_users=[] # Initialize new list of users not in dictionary 
for user in receiver: # All senders are in the dictionary so just loop through recivers
	if user not in dict_list:
		unverified_users.append(user) # if the user isnt in the dict then add them to the new list
unverified_users = list(dict.fromkeys(unverified_users)) # Filter the new list for duplicates

valid_dict = primevalidate(unverified_users, valid_dict)

old_valid_list = []
for key,value in valid_dict.items():
	if value == True:
		old_valid_list.append(key.lower())
old_valid_list = [each for each in old_valid_list if each in all_handles]

new_valid_list = []
for key,value in valid_dict_new.items():
	if value == True:
		new_valid_list.append(key.lower())

new_valid_list.sort()
old_valid_list.sort()

print(len(old_valid_list))
print(len(new_valid_list))

#print(old_valid_list)
#print('\n')
#print(new_valid_list)

for each in old_valid_list:
	if each not in new_valid_list:
		print(each)