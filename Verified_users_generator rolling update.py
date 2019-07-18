#Verified rolling update
#Tom Wallace
#Created 25/06/2019
#Description: This finds all verified users by getting the folliwing list of of @verified - https://twitter.com/verified/following, it then stores this as a pickle file before making a call for each ID to check they exist and are verified. The final result is a dictonary stored as a JSON
#The results dictonary is in the format {'id':'username'} and only contains valid users. Invalid or nonexistant IDs are stored in seperate txt files.

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
import itertools

#####Parameters and settings####
tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication
#tokenpath = 'C:/Users/Zippo/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json'

output_path = './Data/Valid_twitter_handles/' # This is where all data is stores
if not os.path.exists(output_path): # If the path doesn't exist, make it
	print('Output path does not exist, quitting.')
	quit()

sleep_time = 10 # How long to sleep for between each 100 handles in the collector (getValidHandles). Ratelimiting should be automatic but this is good practise.

#####Functions#####
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

def getIDs(api, usepickleIDs):
	#This asks the API for all users being followed by @verified. The return is a large list of IDs.
	print('Getting list of valid IDs from API. Please wait...\n')
	valid_ids_list = []
	
	#page=0
	#while page == 0:
	#	try:
	for result in tweepy.Cursor(api.friends_ids, screen_name="verified").items(): # This line actually makes the calls, using the tweepy cursor to paginate automatically.
		valid_ids_list.append(result) # Each result is a single ID, append it to a list
		if len(valid_ids_list) % 10000 == 0: # This just prints some check messages every 10,000 IDs
			print('Length of list:',len(valid_ids_list)) # This is the length of the list
			print('Length of set: ',len(set(valid_ids_list))) # This is the set (unique entries in the list) which is used to check for duplicates - they do occur
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

	pickle.dump(valid_ids_list, open(output_path + 'validIDs', 'wb')) # At the end save over the pickle file with the new data

def getValidHandles(api, valid_ids_list,valid_screen_names, invalid_count, error_count):
	#This function runs a big loop with the lsit of IDs and makes an API call for each one, getting back more detailed info to check the user exists and is actually verified as the @verified account doesn't seem to stay up to date.
	counter=1 # Basic counter for the loop

	for user_id in valid_ids_list: # Big loop
		userinfo = 0 # This is a constant used to operate the error handling.
		errorcount=0 # This is an internal error counter, different from the one above, and is used to decide when to sleep or try again

		try:
			userinfo = api.get_user(id=user_id) # This is the actual API call, giving it the ID and asking for a single user object
		except tweepy.TweepError as e:
			if e.api_code == 50 or e.api_code == 63: # API code 50 is user not found, 63 is user suspended
				print('>>> ERROR: User not found:',user_id)
				error_count=error_count+1
				with open(output_path+'Error_users_IDs.txt','a') as error_file: # Write the not found user's ID to text
					error_file.write(str(user_id)+'\n')
				continue # Move to the next ID in the big loop
			else: # If the error is unknown then sleep for a bit and try again
				print('>>> WARN: Unhandled error code, exiting. Error ID:', user_id, 'Code:',e)
				quit()

		if userinfo.verified==True: # Some of the users are not acatually validated - this check if they are
			#valid_screen_names.append(userinfo.screen_name) # this contructs a list if just handles
			valid_screen_names.update({user_id : userinfo.screen_name}) # This constructs the results dictonary of {'ID':'handle'}
		elif userinfo.verified==False: # If they are invalid then write their ID to a text file
			print('Non-validated user:',userinfo.screen_name)
			invalid_count=invalid_count+1
			with open(output_path+'Invalid_users_IDs.txt','a') as invalid_file:
				invalid_file.write(str(user_id)+'\n')
		else: # IF the user object doesn't have a vlaid field then write an error
			print('>>> ERROR:',userinfo.screen_name)
			error_count=error_count+1
			with open(output_path+'Error_users_IDs.txt','a') as error_file:
				error_file.write(str(user_id)+'\n')

		if counter % 100 == 0: # Every 100 hadles print an update and sleep
			timenow = datetime.now()
			print(counter, 'of', len(valid_ids_list), '| Time now:',timenow, '| Elapsed time:', timenow-startitme, '| Estimated end:', timenow+(((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)), '| Finished in:', (((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter))) # This complex line works out roughly how much time is left and when the script will finish.
			sleep(sleep_time)
		if counter % 500 == 0: # Every 500 handles save the current dictonary to a temp JSON, the script can be restarted from this if it fails.
			with open(output_path+'valid_screennames_temp.json', 'w', encoding='1252') as outfile:
				json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)
				api = athenticate(tokenpath) # re-authenticate every 500
		counter=counter+1 # Inciment the main counter

	return valid_screen_names, invalid_count, error_count # Return the dictonary and some coutners for validation

#####Main#####
#Start and authenticate
startitme = datetime.now()
print('=======================================================================')
print('Run started at:',startitme)
api = athenticate(tokenpath)

#Get IDs
valid_ids_list = getIDs(api,usepickleIDs)

print('Number of IDs:',len(valid_ids_list))
len_id_set = len(set(valid_ids_list))
print('Number of unique IDs',len_id_set) 

if len(valid_ids_list) != len(set(valid_ids_list)): # Check for duplicates
	duplicates = [item for item, count in collections.Counter(valid_ids_list).items() if count > 1] # Get the duplicate handles in a list
	print('WARN: There are duplicates in the list of IDs, using the set.')
	print('Duplicate IDs:',duplicates)

print('IDs list taking',sys.getsizeof(valid_ids_list)/100000, 'mb of memory\n--------------------------------\n') # Show the size of the list of IDs, should esily fit in memory

quit()

#Filtering - previous valid from temp JSON
if os.path.isfile(output_path+'valid_screennames_temp.json')==True:
	with open(output_path+'valid_screennames_temp.json') as json_file:  
	    valid_screen_names = json.load(json_file) # If there already is a temp file then read it and pull in the partially collected dictoanry
	    IDlist_alreadycollected = [each for each in valid_screen_names.keys()] # Get the already collected keys in a list so they can be filtered

	print('Filtering list of IDs, please wait...\n')

	#valid_ids_list = list(filter(lambda x: x in IDlist_alreadycollected, valid_ids_list))
	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in IDlist_alreadycollected] # Filter IDs already collected
	print(len(IDlist_alreadycollected), 'IDs had already been collected and have been filtered.')
else:
	valid_screen_names={}
#Filtering invalid users
if os.path.isfile(output_path+'Invalid_users_IDs.txt')==True: # Do the same with the list of invalid users, pull in the list and filter them
	with open(output_path+'Invalid_users_IDs.txt', 'r') as invalid_file:
		invalid_ids = invalid_file.read().split('\n')
		invalid_file.close()
	del invalid_ids[-1] # the last item is always a blank line becasue of the \n used to seperate the items when writing the text file, so remvoe it

	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in invalid_ids] # The actual filter
	print(len(invalid_ids), 'IDs have already been marked as invalid and have been filtered.')
	invalid_count = len(invalid_ids)
else:
	invalid_count = 0

#Filtering nonexistant or banned users
if os.path.isfile(output_path+'Error_users_IDs.txt')==True: # Do the same with the list of invalid users, pull in the list and filter them
	with open(output_path+'Error_users_IDs.txt', 'r') as error_file:
		error_ids = error_file.read().split('\n')
		error_file.close()
	del error_ids[-1] # the last item is always a blank line becasue of the \n used to seperate the items when writing the text file, so remvoe it

	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in error_ids] # The actual filter
	print(len(error_ids), 'IDs have already been marked as errors or nonexistant and have been filtered.')
	error_count = len(error_ids)
else:
	error_count=0 # How many non-existant or other errors there have been

#Get handles
print('Collecting handles...\n')
poststarttime = datetime.now()

valid_screen_names,invalid_count,error_count = getValidHandles(api, valid_ids_list, valid_screen_names, invalid_count, error_count)

print('\n--------------------------------\nNumber of screen names collected:',len(valid_screen_names))
print('Number of invalid users:',invalid_count)
print('Number of errors:',error_count)
print('Inital ID list length:', len_id_set, '| Dictonary length + invalid + error:', len(valid_screen_names) + invalid_count + error_count, '| Lengths match:', len_id_set==len(valid_screen_names) + invalid_count + error_count) # Check the results add up to the ID list
print('Results dictonary taking',sys.getsizeof(valid_screen_names)/100000, 'mb of memory\n')
print('End time:',datetime.now(),'Time taken:',(datetime.now())-startitme)
print('Writing results dictonary to JSON.')
print('=======================================================================')

with open(output_path+'valid_screennames.json', 'w', encoding='1252') as outfile: # Write the final output dictonary to JSON 
    json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)


####Application####
"""
#This block reads the JSON back in and get's the handles as a list - this is how the results should be used in other scripts
with open(output_path+'valid_screennames.json') as json_file:  
    valid_screen_names = json.load(json_file)
    print(valid_screen_names)
    print(type(valid_screen_names))

    handlelist = [each for each in valid_screen_names.values()]
    print(handlelist)

"""