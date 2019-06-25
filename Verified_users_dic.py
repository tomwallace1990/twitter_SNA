#List of verified users
#Tom Wallace
#Created 25/06/2019
#Description: This finds all verified users by getting the folliwing list of of @verified - https://twitter.com/verified/following, it then stores this in a json for use in other scripts

#####Imports#####
import tweepy
import json
from datetime import datetime
import sys

#####Parameters and settings####
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

#####Main#####
startitme = datetime.now()
print('=======================================================================')
print('Run started at:',startitme)
api = athenticate(tokenpath)

valid_ids_list = []
for page in tweepy.Cursor(api.friends_ids, screen_name="verified").pages(): # come in block of 5000
	valid_ids_list.extend(page)
	if len(valid_ids_list) > 10000:
		break

print('Number of IDs collected:',len(valid_ids_list))
print('IDs list taking',sys.getsizeof(valid_ids_list)/100000, 'mb of memory\n--------------------------------\n')

#valid_ids_list=valid_ids_list[:1000] #TEMP

valid_screen_names=[]
counter=1
invalid_count=0
for user_id in valid_ids_list:
	userinfo = api.get_user(id=user_id)
	if userinfo.verified==True:
		valid_screen_names.append(userinfo.screen_name)
	else:
		print('>>> Invalid user:',userinfo.screen_name)
		invalid_count=invalid_count+1
	if counter % 100 == 0:
		timenow = datetime.now()
		print(counter, 'of', len(valid_ids_list), '| Time now:',timenow, '| Elapsed time:', timenow-startitme, '| Estimated end:', timenow+(((timenow-startitme)/counter)*((len(valid_ids_list))-counter)), '| Finished in:', (((timenow-startitme)/counter)*((len(valid_ids_list))-counter)))
	counter=counter+1

print('\n--------------------------------\nNumber of screen names collected:',len(valid_screen_names))
print('Names list taking',sys.getsizeof(valid_screen_names)/100000, 'mb of memory\n')
print('Number of invalid users:',invalid_count)
print('End time:',datetime.now(),'Time taken:',(datetime.now())-startitme)
print('=======================================================================')

with open('./Data/valid_screennames.json', 'w', encoding='1252') as outfile:
    json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)

