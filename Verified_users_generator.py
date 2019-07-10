#List of verified users
#Tom Wallace
#Created 25/06/2019
#Description: This finds all verified users by getting the folliwing list of of @verified - https://twitter.com/verified/following, it then stores this in a json for use in other scripts

#To update it, call the users details to find out the following numnber, count the len of the current list, work out how many need to get and just grab that many
#Or may need to do a full scan to ensure none have been removed

#####Imports#####
import tweepy
import json
from datetime import datetime
import sys
import os
from time import sleep
import pickle
import collections

#####Parameters and settings####
#tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication
tokenpath = 'C:/Users/Zippo/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json'

output_path = './Data/Valid_twitter_handles/'
if not os.path.exists(output_path): # If the path doesn't exist, make it
	os.makedirs(output_path)

usepickleIDs = True
sleep_time = 10 # How long to sleep for between each 100 handles in the collector (getValidHandles)

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

def getIDs(api, usepickleIDs):
	if usepickleIDs == False:
		print('Getting list of valid IDs from API. Please wait...\n')
		valid_ids_list = []
		
		#page=0
		#while page == 0:
		#	try:
		for result in tweepy.Cursor(api.friends_ids, screen_name="verified").items(): # 325655
			valid_ids_list.append(result)
			if len(valid_ids_list) % 10000 == 0:
				print('Length of list:',len(valid_ids_list))
				print('Length of set: ',len(set(valid_ids_list)))
				sleep(5)
			#if len(valid_ids_list) >=325655: # if this works add an API call to the start to find the number of follows live on twitter
			#	page=1
			#	break
				#if len(valid_ids_list) >= 5000: # this stops the list growing for testing
				#	break
		#	except:
		#		print('WARN: Error, sleeping for 30 seconds...')
		#		sleep(30)
		#		page=0

		pickle.dump(valid_ids_list, open(output_path + 'validIDs', 'wb'))
	else:
		if os.path.isfile(output_path + 'validIDs')==True:
			print('Using pickled ID data.\n')
			valid_ids_list = pickle.load(open(output_path + 'validIDs', 'rb'))
		else:
			print('WARN: No pickle data found. Downloading data.')
			valid_ids_list = getIDs(api,usepickleIDs==False) # if there is no file the function is called again with the variable flipped to false so it will be collected 
	return valid_ids_list

def getValidHandles(api, valid_ids_list,valid_screen_names):
	counter=1
	invalid_count=0
	error_count=0

	for user_id in valid_ids_list:

		userinfo = 0
		errorcount=0

		while userinfo==0: # This block of code makes the script robust to disconnection - it will keep trying and sleeping forever so keep an eye on it.
			try:
				userinfo = api.get_user(id=user_id)
			except tweepy.TweepError as e:
				if e.api_code == 50:
					break
				else:
					print('>>> WARN: Disconnected, sleeping for 10 seconds <<<')
					sleep(10)
					errorcount = errorcount + 1
					if errorcount==5:
						print('>>> WARN: Multiple disconnections, sleeping for 30 mins <<<')
						sleep(30*60)
						errorcount=0
						api = athenticate(tokenpath)
						sleep(5)
					else:
						pass	
		if userinfo == 0:
			print('>>> ERROR: User not found:',user_id)
			error_count=error_count+1
			with open(output_path+'Error_users_IDs.txt','a') as error_file:
				error_file.write(str(user_id)+'\n')
			continue
		if userinfo.verified==True:
			#valid_screen_names.append(userinfo.screen_name) # this contructs a list if just handles
			valid_screen_names.update({user_id : userinfo.screen_name}) # this constructs a dictonary of ID:handle
		elif userinfo.verified==False:
			print('Non-validated user:',userinfo.screen_name)
			invalid_count=invalid_count+1
			with open(output_path+'Invalid_users_IDs.txt','a') as invalid_file:
				invalid_file.write(str(user_id)+'\n')
		else:
			print('>>> ERROR:',userinfo.screen_name)
			error_count=error_count+1
			with open(output_path+'Error_users_IDs.txt','a') as error_file:
				error_file.write(str(user_id)+'\n')

		if counter % 100 == 0:
			timenow = datetime.now()
			print(counter, 'of', len(valid_ids_list), '| Time now:',timenow, '| Elapsed time:', timenow-startitme, '| Estimated end:', timenow+(((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)), '| Finished in:', (((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)))
			sleep(sleep_time)
		if counter % 500 == 0:
			with open(output_path+'valid_screennames_temp.json', 'w', encoding='1252') as outfile:
				json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)
				api = athenticate(tokenpath)
		counter=counter+1

	return valid_screen_names, invalid_count, error_count

#####Main#####

#Start and authenticate
startitme = datetime.now()
print('=======================================================================')
print('Run started at:',startitme)
api = athenticate(tokenpath)

#Get IDs
valid_ids_list = getIDs(api,usepickleIDs)

print('Number of IDs:',len(valid_ids_list))
print('Number of unique IDs',len(set(valid_ids_list)))

if len(valid_ids_list) != len(set(valid_ids_list)):
	duplicates = [item for item, count in collections.Counter(valid_ids_list).items() if count > 1]
	print('WARN: There are duplicates in the list of IDs, using the set.')
	print('Duplicate IDs:',duplicates)

print('IDs list taking',sys.getsizeof(valid_ids_list)/100000, 'mb of memory\n--------------------------------\n')

#valid_ids_list = valid_ids_list[:1200]

#Filtering - previous valid from temp JSON
if os.path.isfile(output_path+'valid_screennames_temp.json')==True:
	with open(output_path+'valid_screennames_temp.json') as json_file:  
	    valid_screen_names = json.load(json_file)
	    IDlist_alreadycollected = [each for each in valid_screen_names.keys()]

	print('Filtering list of IDs, please wait...\n')
	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in IDlist_alreadycollected]
	print(len(IDlist_alreadycollected), 'IDs had already been collected and have been filtered.')
else:
	valid_screen_names={}
#Filtering invalid users
if os.path.isfile(output_path+'Invalid_users_IDs.txt')==True:
	with open(output_path+'Invalid_users_IDs.txt', 'r') as invalid_file:
		invalid_ids = invalid_file.read().split('\n')
		invalid_file.close()
	del invalid_ids[-1] # the last item is always a blank line becasue of the \n used to seperate the items when writing the text file, so remvoe it

	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in invalid_ids]
	print(len(invalid_ids), 'IDs have already been marked as invalid and have been filtered.')

#Get handles
print('Collecting handles...\n')
poststarttime = datetime.now()
valid_screen_names,invalid_count,error_count = getValidHandles(api, valid_ids_list,valid_screen_names)

print('\n--------------------------------\nNumber of screen names collected:',len(valid_screen_names))
print('Number of invalid users:',invalid_count)
print('Number of errors:',error_count)
print('Inital ID list length:', len(valid_ids_list), '| Dictonary length + invalid + error:', len(valid_screen_names) + invalid_count + error_count, '| Lengths match:', len(valid_ids_list)==len(valid_screen_names) + invalid_count + error_count)
print('Results dictonary taking',sys.getsizeof(valid_screen_names)/100000, 'mb of memory\n')
print('End time:',datetime.now(),'Time taken:',(datetime.now())-startitme)
print('Writing results dictonary to JSON.')
print('=======================================================================')

with open(output_path+'valid_screennames.json', 'w', encoding='1252') as outfile:
    json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)


"""
with open(output_path+'valid_screennames.json') as json_file:  
    valid_screen_names = json.load(json_file)
    print(valid_screen_names)
    print(type(valid_screen_names))

    handlelist = [each for each in valid_screen_names.values()]
    print(handlelist)

"""