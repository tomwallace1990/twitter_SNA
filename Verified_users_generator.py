#Verified_users_generator
#Tom Wallace
#Created 25/06/2019
#Description: This finds all verified users by getting the following list of the account @verified - https://twitter.com/verified/following, it then stores this as a pickle file before making a call for each ID to check they exist and are verified. The final result is a dictionary stored as a JSON
#The results dictionary is in the format {'id':'username'} and only contains valid users. Invalid or non-existent IDs are stored in separate txt files for logging purposes.

#Tasks done
#	0. Basic functionality, downloads IDs, then loops through them  making a call for each to check the user is valid and get their handle.
#	1. Error handling for not found or suspended users
#	2. Hot restart - will read in temp JSON and error txt files and exclude those from the list

#To do for the future
#	1. Work out why getIDs sometimes returns duplicates rather than the full list. Seems to be when @verified adds more users during a run, which changes the length of the list, but new users being added and duplicates appearing don't exactly coincide. May be a problem internal to the API or Tweepy. Can try and find a solution or develop a workaround, probably which makes several runs and combines them.
#	2. Keeping the dictionary up to date
#	2.1. Get new IDs - get IDs list for newly added IDs (based on where old list left off) and make API calls to get handles, should take a couple of minutes.
#	2.2. Check IDs list - get the whole ID list and compare it to the stored one. Remove any removed IDs and make API calls to get the handle of any new IDs should take around an hour.
#	2.3. Check for handle changes - handles can occasionally change so the dictionary will slowly go out of date, to update this the whole scan will need to be performed again with the dictionary being built fresh, will take 4-5 days.

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
output_path = './Data/Valid_twitter_handles/' # This is where all data is stored
if not os.path.exists(output_path): # If the path doesn't exist, make it based on where the script is on disk
	os.makedirs(output_path)

usepickleIDs = False # bool. This is a 2-stage scrip, get all IDs (takes an hour) and then get all handles (takes a few days). This option will allow it to skip collecting IDs and use the last saved copy. Useful if doing multiple runs to complete stage 2.
sleep_time = 10 # int. How long to sleep for between each 100 handles in the collector (getValidHandles). Rate limiting should be automatic but this is good practice.

#####Functions#####
def athenticate(tokenpath):
	#This simply authenticates with the API and returns an API wrapper object. Stored in a function as it is sometimes called to re-authenticate over long runs.	
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
	#This asks the API for all users being followed by @verified. The return is a large list of IDs which is dumped to disk in a pickle file.
	if usepickleIDs == False: # If want to collect fresh data...
		print('Getting list of valid IDs from API. Please wait...\n')
		valid_ids_list = []
		
		for result in tweepy.Cursor(api.friends_ids, screen_name="verified").items(): # This line actually makes the calls, using the Tweepy cursor to paginate automatically.
			valid_ids_list.append(result) # Each result is a single ID, append it to a list
			if len(valid_ids_list) % 10000 == 0: # This just prints some progress messages every 10,000 IDs
				print('Length of list:',len(valid_ids_list)) # This is the length of the list
				userinfo = api.get_user(screen_name='verified') # BUG TESTING - the script seems to error if @verified adds more following during the run, this calls their info ever 10,000 to keep tabs on them
				print('Num to get:', userinfo.friends_count) # BUG TESTING - this prints the number of users @verified is following to check if it has changed
				if len(valid_ids_list) != len(set(valid_ids_list)): # If @verified adds following then the results contain duplicates - this checks if there are any duplicates
					print('WARN:',len(valid_ids_list)-len(set(valid_ids_list)), 'duplicates returned.\n') # This prints the number of duplicates

		pickle.dump(valid_ids_list, open(output_path + 'validIDs', 'wb')) # At the end save the pickle file with the data, this will automatically overwrite the previous pickle file
	else: # If want to use the old pickle file...
		if os.path.isfile(output_path + 'validIDs')==True: # Check if the pickle file exists
			print('Using pickled ID data.\n')
			valid_ids_list = pickle.load(open(output_path + 'validIDs', 'rb')) # If the file is actually there then load it
		else:
			print('WARN: No pickle data found. Downloading data.')
			valid_ids_list = getIDs(api,usepickleIDs==False) # If there is no pickle file, the function is called again with the variable flipped to false so it will be collected 
	return valid_ids_list # return the list of IDs

def getValidHandles(api, valid_ids_list,valid_screen_names, invalid_count, error_count):
	#This function runs a big loop with the list of IDs and makes an API call for each one, getting back more detailed info to check the user exists and is actually verified as the @verified account follows some users who are not verified (these may have been verified in the past or could simply be mistakes).
	counter=1 # Basic counter for the loop

	for user_id in valid_ids_list: # Big loop
		userinfo = 0 # This is an int used to operate the error handling.

		try:
			userinfo = api.get_user(id=user_id) # This is the actual API call, giving it the ID and asking for a single user object
		except tweepy.TweepError as e: # the API should return informative errors
			if e.api_code == 50 or e.api_code == 63: # API code 50 is user not found, 63 is user suspended.
				print('>>> ERROR: User not found:',user_id)
				error_count=error_count+1
				with open(output_path+'Error_users_IDs.txt','a') as error_file: # Write the not found user's ID to the error txt
					error_file.write(str(user_id)+'\n')
				continue # Move to the next ID in the big loop and skip the code below
			else: # If the error is unknown then exit - the error may need to be added to the if statement above, or there could be a wider problem like Twitter being down
				print('>>> WARN: Unhanded error code, exiting. Error ID:', user_id, 'Code:',e)
				quit()

		#By this point in the loop userinfo should contain a user object
		if userinfo.verified==True: # Some of the users are not actually validated - this check if they are
			valid_screen_names.update({user_id : userinfo.screen_name}) # This constructs the results dictionary of {'ID':'handle'}
		elif userinfo.verified==False: # If they are invalid then write their ID to a txt file
			print('Non-validated user:',userinfo.screen_name)
			invalid_count=invalid_count+1
			with open(output_path+'Invalid_users_IDs.txt','a') as invalid_file:
				invalid_file.write(str(user_id)+'\n')
		else: # If the user object doesn't have a valid field then write an error
			print('>>> ERROR:',userinfo.screen_name)
			error_count=error_count+1
			with open(output_path+'Error_users_IDs.txt','a') as error_file:
				error_file.write(str(user_id)+'\n')

		if counter % 100 == 0: # Every 100 handles print an update and sleep
			timenow = datetime.now()
			print(counter, 'of', len(valid_ids_list), '| Time now:',timenow, '| Elapsed time:', timenow-startitme, '| Estimated end:', timenow+(((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter)), '| Finished in:', (((timenow-poststarttime)/counter)*((len(valid_ids_list))-counter))) # This complex line works out roughly how much time is left and when the script will finish.
			sleep(sleep_time)
		if counter % 500 == 0: # Every 500 handles save the current dictionary to a temp JSON, the script can be restarted from this if it fails deep into a run.
			with open(output_path+'valid_screennames_temp.json', 'w', encoding='1252') as outfile:
				json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)
				api = athenticate(tokenpath) # re-authenticate every 500
		counter=counter+1 # Increment the main counter

	return valid_screen_names, invalid_count, error_count # Return the dictionary and some counters for validation

#####Main#####
#Start and authenticate
startitme = datetime.now()
print('=======================================================================')
print('Run started at:',startitme)
api = athenticate(tokenpath)

#Get IDs
valid_ids_list = getIDs(api,usepickleIDs) # Get the list of IDs @verified is following by calling the function

print('Number of IDs:',len(valid_ids_list)) # Print how many IDs were collected

if len(valid_ids_list) != len(set(valid_ids_list)): # Check for duplicates
	print('Number of unique IDs',len(set(valid_ids_list))) # Print the length of the set to spot duplicates
	duplicates = [item for item, count in collections.Counter(valid_ids_list).items() if count > 1] # Get the duplicate handles in a list
	print('WARN: There are duplicates in the list of IDs, using the set.')
	print('Duplicate IDs:',duplicates) # More work is needed in getIDs to find out why it is returning duplicates

print('IDs list taking',sys.getsizeof(valid_ids_list)/100000, 'mb of memory\n--------------------------------\n') # Show the size of the list of IDs, should easily fit in memory

#Filtering: if some of the IDs have already been collected, or marked as invalid or errors, then strip these out. To perform a fresh run delete the temp and error files
#Filtering - previous valid IDs from temp JSON - this could be a large number if a previous run went deep
if os.path.isfile(output_path+'valid_screennames_temp.json')==True:
	with open(output_path+'valid_screennames_temp.json') as json_file:  
	    valid_screen_names = json.load(json_file) # If there already is a temp file then read it and pull in the partially collected dictionary
	    IDlist_alreadycollected = [each for each in valid_screen_names.keys()] # Get the already collected keys in a list so they can be filtered

	print('Filtering list of IDs, please wait...\n')
	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in IDlist_alreadycollected] # Filter IDs already collected, can take several minutes
	print(len(IDlist_alreadycollected), 'IDs had already been collected and have been filtered.')
else:
	valid_screen_names={} # If there was no previous results then initialize an empty dictionary to be passed to the getValidHandles function

#Filtering invalid users
if os.path.isfile(output_path+'Invalid_users_IDs.txt')==True: # Do the same with the list of invalid users, pull in the list from the txt file and filter them
	with open(output_path+'Invalid_users_IDs.txt', 'r') as invalid_file:
		invalid_ids = invalid_file.read().split('\n')
		invalid_file.close()
	del invalid_ids[-1] # the last item is always a blank line because of the \n used to separate the items when writing the text file, so remove it

	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in invalid_ids] # The actual filter
	print(len(invalid_ids), 'IDs have already been marked as invalid and have been filtered.')
	invalid_count = len(invalid_ids)
else:
	invalid_count = 0 # If no invalid file found then current value of invalid counter is 0

#Filtering non-existent or banned users
if os.path.isfile(output_path+'Error_users_IDs.txt')==True: # Do the same with the list of error users, pull in the list and filter them
	with open(output_path+'Error_users_IDs.txt', 'r') as error_file:
		error_ids = error_file.read().split('\n')
		error_file.close()
	del error_ids[-1] # the last item is always a blank line because of the \n used to separate the items when writing the text file, so remove it

	valid_ids_list = [idnum for idnum in valid_ids_list if str(idnum) not in error_ids] # The actual filter
	print(len(error_ids), 'IDs have already been marked as errors or non-existent and have been filtered.')
	error_count = len(error_ids)
else:
	error_count=0 # If no error file found then current number of errors is 0

#Get handles
print('Collecting handles...\n')
poststarttime = datetime.now() # This is the start time of the handle collection

valid_screen_names,invalid_count,error_count = getValidHandles(api, valid_ids_list, valid_screen_names, invalid_count, error_count)

print('\n--------------------------------\nNumber of screen names collected:',len(valid_screen_names))
print('Number of invalid users:',invalid_count)
print('Number of errors:',error_count)
print('Initial ID list length:', len_id_set, '| Dictionary length + invalid + error:', len(valid_screen_names) + invalid_count + error_count, '| Lengths match:', len_id_set==len(valid_screen_names) + invalid_count + error_count) # Check the results add up to the ID list
print('Results dictionary taking',sys.getsizeof(valid_screen_names)/100000, 'mb of memory\n')
print('End time:',datetime.now(),'Time taken:',(datetime.now())-startitme)
print('Writing results dictionary to JSON.')
print('=======================================================================')

with open(output_path+'valid_screennames.json', 'w', encoding='1252') as outfile: # Write the final output dictionary to JSON 
    json.dump(valid_screen_names, outfile, ensure_ascii=False, indent=2)


####Application examples####
"""
#This block reads the JSON back in and gets the handles as a list - this is how the results should be used in other scripts
with open(output_path+'valid_screennames.json') as json_file:  
    valid_screen_names = json.load(json_file)
    print(valid_screen_names)
    print(type(valid_screen_names))

    handlelist = [each for each in valid_screen_names.values()]
    print(handlelist)


def validate(valid_dict, all_handles):
	#This is the valid dictionary being used in a function to filter handles
	with open('./valid_screennames.json') as json_file:  
	    valid_screen_names = json.load(json_file)
	    validlist = [each.lower() for each in valid_screen_names.values()]

	for handle in all_handles:
		if handle.lower() in validlist:
			valid_dict.update({handle.lower() : True})
		else:
			valid_dict.update({handle.lower() : False})

	return valid_dict
"""