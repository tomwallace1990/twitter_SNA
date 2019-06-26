#List of verified users
#Tom Wallace
#Created 25/06/2019
#Description: This finds all verified users by getting the folliwing list of of @verified - https://twitter.com/verified/following, it then stores this in a json for use in other scripts

#####Imports#####
import tweepy
import json
from datetime import datetime
import sys
import os
from time import sleep

#####Parameters and settings####
#tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication
tokenpath = 'C:/Users/Zippo/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json'

output_path = './Data/'
if not os.path.exists(output_path): # If the path doesn't exist, make it
	os.makedirs(output_path)

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
	#if len(valid_ids_list) > 10000: # this stops the list growing for testing
	#	break

print('Number of IDs collected:',len(valid_ids_list))
print('IDs list taking',sys.getsizeof(valid_ids_list)/100000, 'mb of memory\n--------------------------------\n')

poststarttime = datetime.now()

valid_screen_names=[]
counter=1
invalid_count=0
for user_id in valid_ids_list:
	
	userinfo = 0
	errorcount=0

	while userinfo==0: # This block of code makes the script robust to disconnection - it will keep trying and sleeping forever so keep an eye on it.
		try:
			userinfo = api.get_user(id=user_id)
		except:
			print('Disconnected, sleeping for 5 seconds')
			sleep(5)
			errorcount = errorcount + 1
			if errorcount==3:
				print('Multiple disconnections, sleeping for 30 mins')
				sleep(30*60)
				errorcount=0
			else:
				pass	

	if userinfo.verified==True:
		valid_screen_names.append(userinfo.screen_name)
	else:
		print('>>> Non-validated user:',userinfo.screen_name)
		invalid_count=invalid_count+1
	if counter % 100 == 0:
		timenow = datetime.now()
		print(counter, 'of', len(valid_ids_list), '| Time now:',timenow, '| Elapsed time:', timenow-startitme, '| Estimated end:', timenow+(((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)), '| Finished in:', (((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)))
	if counter % 1000 ==0:
		with open(output_path+'valid_screennames_temp.json', 'w', encoding='1252') as outfile:
			json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)
			api = athenticate(tokenpath)
	counter=counter+1

print('\n--------------------------------\nNumber of screen names collected:',len(valid_screen_names))
print('Names list taking',sys.getsizeof(valid_screen_names)/100000, 'mb of memory\n')
print('Number of invalid users:',invalid_count)
print('End time:',datetime.now(),'Time taken:',(datetime.now())-startitme)
print('=======================================================================')

with open(output_path+'valid_screennames.json', 'w', encoding='1252') as outfile:
    json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)