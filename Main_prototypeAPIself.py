#Main
#Tom Wallace
#Created 28/05/2019
#Description: This is a prototype for detecting influencers in twitter data.

#Other ideas
# Where am i in network given a topic (autosearching)
# Time (REMs), event detection 
# 


#To do:

#	3. Spike detection - automate selection of preiod
#	5. Rolling data input - last 3 days for example
#	6. Interface - leave to Barrachd, I'll do backend
#	9. Follower/following networks
#	10. Get data from platfrom - set up query on alerter
#	12. Switch to be about given username
#	14. Replace hashes in output


#Done
#	0. Basic functionality - read in data, manage data, build edge list, build network, compute metrics, print metrics
#	2. Self links - toggle to allow or disallow - currenrly disallowed
#	1. Duplicated tweet and bots - set a toggle to allow or disallow them
#	4. Currently no edge weighting - repeated contact not taken into account
#	7. Hash usernames to protect identity
#	8. Toggle on/off or mark retweets - do they already do this? added to the searchtwit function in Bluetick.py
#	13. Capitalisation
#	11. Identify verified users

#####Imports#####
import pandas as pd
import re
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import hashlib
import json
import tweepy
import pickle
from time import sleep
import random

#####Parameters and settings#####
selfloop = False # bool. This sets whether to allow self loops, if 'True' tweets with no '@' (someone just tweeting but not mentioning another user) will be added to the edge list as 'author':'author' showing a left link. If 'False' these tweets will be excluded from the egde list
noresults = 10 # int. number of results to show
removedups = False # bool. This removes duplicate tweets which are often bots, it looks for identical text content (even from different accounts) but excludes URLs.
edgeweighting = False # bool. This set whether to allow repeated contact between accounts to be accounted for, SNA analysis usually does not but 'True' is probably best default here
user_search_sleep = 0 # How long to sleep for when looping over users and making API calls
max_tweets = 2500 # How many tweets to request
query = 'Extinction rebellion' # Topic of the request
allowRTs = True # Allow retweets or not, will reduce number of tweets imported below value of 'max_tweets' as it filters after the import
hashing_type = 'valid' # none, full, valid - type of hasing to apply. None: show all usernames. Full: show no usernames. valid: show valid users only (default).
given_user = 'ajplus' # The input user to return results for

projectpath = './' # Set the root folder
inputfile = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019.csv' # Manually set the input file
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

def searchtwit(query, max_tweets, allowRTs):
	
	print('Searcing twitter for', max_tweets, 'tweets on the topic of', query)
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

def edgelister(authors, tweets, selfloop=False, removedups=False, sav_path=None): 
	# This function takes tweet objects and generates an edgelist, which is a pair of equal length lists showing the sender and receiver of each tweet which contains one or more '@'
	# Where there is more than one '@' in a tweet an equal number of lines is created in the edge list
	# This function expects a list of string handles and a matching list of tweet text.
	# Example: the tweet 'hi, this is a test @test @testing' by account tomw would result in the lists - [tomw, tomw] [test, testing] 

	sender, receiver=[], []

	if removedups == True:
		print(len(tweets))
		urlmatch = re.compile(r'(https|http)://([^\s]+)')
		tweets = [re.sub(r'(https|http)://([^\s]+)', 'URL', tweet) for tweet in tweets]
		tweets = list(dict.fromkeys(tweets))
		print(len(tweets))

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

def prevalidate (valid_dict, searched_tweets):

	for tweet in searched_tweets:
		valid_dict.update({tweet.user.screen_name.lower() : tweet.user.verified})
		if re.match('RT @', tweet.text) is not None:
			valid_dict.update({tweet.retweeted_status.user.screen_name.lower() : tweet.retweeted_status.user.verified})

	return valid_dict

def primevalidate (users, valid_dict, user_search_sleep):

	print('Making API calls for ', len(users), ' users. Please wait.', sep='')
	for user in users:
		try:
			userinfo = api.get_user(screen_name=user)	
			valid_dict.update({userinfo.screen_name.lower() : userinfo.verified})
		except:
			valid_dict.update({user : None})
		sleep(user_search_sleep)

	return valid_dict

def hasher (sender, receiver, hashing_type, valid_dict):
	if hashing_type == 'valid':
		sender = [hashlib.sha224(handle.encode()).hexdigest() if valid_dict.get(handle)!=True else handle for handle in sender]
		receiver = [hashlib.sha224(handle.encode()).hexdigest() if valid_dict.get(handle)!=True else handle for handle in receiver]
	elif hashing_type == 'full':
		sender = [hashlib.sha224(handle.encode()).hexdigest() for handle in sender]
		receiver = [hashlib.sha224(handle.encode()).hexdigest() for handle in receiver]
	elif hashing_type == 'none':
		pass

	return sender, receiver

def spinnerette(senders, receivers, edgeweighting=False):
	# This function takes in an edge list as a sender and receiver list (as produced by edgelister) and converts them into a network object from the library networkx

	if edgeweighting == True:
		network = nx.MultiDiGraph() # Initalise the network
	else:
		network = nx.DiGraph() # Initalise the network
	
	for sender, receiver in zip(senders,receivers): # Need to use a zip loop again
		network.add_edge(sender, receiver) # Add each edge to the network one by one
	
	return network # Give back to completed network object

def centrality(network):
	# This function calculates centrality metrics based on the network constructed by spinnertte. These metrics are node level (there is a number for each actor in the network) and are returned as a dataframe

	degree = nx.degree_centrality(network) # Degree centrality is the fraction of nodes each given node is connected to, repeated conect is not counted, this is the number of connections not the frequency of contact
	ds_degree = pd.Series(degree)

	in_degree = nx.in_degree_centrality(network) # This is the fraction of nodes which send to a given node, sometimes interpreted as popularity
	ds_in_degree = pd.Series(in_degree)
	
	out_degree = nx.out_degree_centrality(network) # This is the fraction of nodes which a given node sends to, sometimes interpreted as activity
	ds_out_degree = pd.Series(out_degree)

	close = nx.closeness_centrality(network) # This is a measure of centralisation, being in the middle of a network. It is calculated by taking the inverse of the average legnth of the shortest paths between the given node and all other nodes
	ds_close = pd.Series(close)

	between = nx.betweenness_centrality(network) # This is a measure of bridging, linking, or brokerage. It is the number of shortest paths which pass through the given node
	ds_between = pd.Series(between)

	try: # In the test data this throws an erorr - i suspect becasue the data is a bit rubbish and doesn't have enough structure. This try will catch it and return all zeros
		eigen = nx.eigenvector_centrality(network) # This is a measure of prominance, based on similar algorithm to google page rank, probably best all round metric
		ds_eigen = pd.Series(eigen)
	except:
		ds_eigen = pd.Series(0, index=network.nodes)

	df_centrality = pd.concat([ds_degree, ds_in_degree, ds_out_degree, ds_close, ds_between, ds_eigen], axis=1)
	df_centrality.rename(columns = {0:'degree',1:'in degree',2:'out degree',3:'closeness',4:'betweenness',5:'eigenvector'}, inplace = True)

	return df_centrality

def print_results_userlevel(df_centrality):
	df_centrality_width = df_centrality.shape # Get the width of the dataframe as an int - it is used in the loop below. Width is the number of columns/ number of metrics which were calculated
	colnames = list(df_centrality.columns.values) # Get the headers from the data frame so they can be used in the output below - they are set in the centrality function

	df_centrality = df_centrality.sort_values(by=['degree'],ascending=False)
	degree_cent = list(df_centrality['degree'])
	index_list = list(df_centrality.index.tolist())

	print('\n\nYou in the network\n-------------------------')

	counter=1
	for handle in index_list:
		
		if handle!=given_user:
			counter=counter+1
		else:
			break
	print('You are ', counter, ' out of ', len(index_list) ,' for degree centrality. This puts you in the top ', '%.4f' % (100-(counter/len(index_list))), '% of users in this network!', sep='')
	
	print("\nHere's how the top public accounts scored")
	previous_result = []
	random_list = [random.uniform(0, 1) for each in index_list]
	counter_list = list(range(0,len(index_list)))
	result_count=1
	for handle,result,rando,counter in zip(index_list,degree_cent,random_list,counter_list):
		if len(handle) < 56 and handle!=given_user:
			if result_count > 10:
				continue
			print(result_count, '. ', handle, '. Rank: ', counter+1, ' Score: ', '%.4f' % result, sep='')
			result_count=result_count+1
			previous_result.append(handle)
		elif handle==given_user:
			print('\n',result_count, '. \t > You are here! Rank: ', counter+1, ' Score: ', '%.4f' % result, ' <\n', sep='')
			result_count=result_count+1
			previous_result.append(handle)
			given_user_count = counter
	for handle,result,rando,counter in zip(index_list,degree_cent,random_list,counter_list):	
		if given_user in previous_result and handle not in previous_result and counter>given_user_count and len(handle) < 56 and rando <0.2:
			print(result_count, '. ', handle, '. Rank: ', counter+1, ' Score: ', '%.4f' % result, sep='')
			result_count=result_count+1
			if result_count > 20:
				break




	quit()

	print("\nHere's where some public accounts scored lower down")
	random_list = [random.uniform(0, 1) for each in index_list]
	counter=0
	result_count = 1
	for handle,result, rando in zip(index_list,degree_cent, random_list):
		counter=counter+1
		if len(handle) < 56 and handle not in previous_result and rando <0.2:
			print(result_count, '. ', handle, '. Rank: ', counter, ' Score: ', '%.4f' % result, sep='')
			result_count=result_count+1
			if result_count > 10:
				break

	print('\n')
	previous_result = []
	counter_list = list(range(0,len(index_list)))
	result_count = 1
	for handle,result,rando,counter in zip(index_list,degree_cent, random_list,counter_list):
		if len(handle) < 56 and handle !=given_user:
			print(result_count, '. ', handle, '. Rank: ', counter+1, ' Score: ', '%.4f' % result, sep='')
			result_count=result_count+1
			previous_result.append(handle)
			if result_count > 10:
				break


	quit()


	for label,value in zip(colnames, range(0,df_centrality_width[1])): # this loop takes each of the metrics in turn and prints the top 5 accounts for each metric. Effecitvely this is the mian results output
		series_results = df_centrality[df_centrality.columns[value]] # Create a temp series by slicing into the dataframe with the value iterator
		series_results_sort = series_results.sort_values(ascending=False) # reverse sort the temp seires so the top influencers are at the top
		print(value, '. Top ', noresults, ' influential accounts based on ', label, ' centrality.', sep='') #Print a header with the column name for info
		if series_results.sum() == 0: # This if checks if the seires has valid results, if not it will print a warning instead
			print('>>>WARN: Results are all naught. The network may be too small/simple to calculate this metric. <<<')
		elif np.std(series_results_sort[:noresults]) == 0: # This cheks if the results are all the same number, if so the metric lacks variation and an error is shown
			print('>>>WARN: Top', noresults, 'results are all equal. The network may be too small/simple to calculate this metric. <<<')
		else:
			print(series_results_sort[:noresults]) # If it is valid the top 5 influencers will be printed
			influencers = list(series_results_sort[:noresults].index) # These two lines are used for the graphing below, they add the names of the top 5 influencers to a list
			influencers_list.append(influencers)
		print('\n')

#####Main#####
#Authenticate via public API
api = athenticate(tokenpath)

#Grab tweets on given topic from API. Account is list of senders, corpus is matching list of tweet text, searched_tweets is matching list of the full tweet objects
#account, corpus, searched_tweets = searchtwit(query, max_tweets, allowRTs)
#dump_data = zip(account, corpus, searched_tweets)
#pickle.dump(dump_data, open( './tweets', 'wb'))

dump_data = pickle.load(open( './tweets', 'rb'))
account, corpus, searched_tweets = zip(*dump_data)

#Case conversion
account = [text.lower() for text in account]
corpus = [text.lower() for text in corpus]

#Create edge list
sender, receiver = edgelister(account, corpus, selfloop, removedups) # Call the edgelister function to convert the authors and tweets into an edge list
	# to save the data as an edge list, include an output path as option 3 abvoe such as outputpath = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019UTF8_edgelist.csv' 
	# Sender and receiver are not equal length lists showing the asymmetric links

#Validation - prevalidate (get validation from existing tweet objects)
	#Pre validation uses infrom from the already downloaded tweet objects and saves making unnessiary API calls. It reduces the number of calls by more than 90%
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

#valid_dict = primevalidate(unverified_users, valid_dict, user_search_sleep) # Update the dictonary with the extra users, this should be the same length as the number of nodes in the network
#pickle.dump(valid_dict, open( './validdict', 'wb'))
valid_dict = pickle.load(open( './validdict', 'rb'))

#Remove invalid user names
invalid = [handle for handle in (list(set(sender+receiver))) if valid_dict.get(handle)==None] # It is possible to tweet at an invalid handle, these are picked up as part of primevalidate and removed here (only handles in primevalidate are picked up)

for send, rec in zip(sender,receiver): # for each dyadic edge
	for inval in invalid: # for each invalid handle
		if inval in send or inval in rec: #if either part of the dyad is invalid remove the whole dyad
			sender.remove(send)
			receiver.remove(rec)

#Hash usernames
sender, receiver = hasher(sender, receiver, hashing_type, valid_dict)

#Create network
network = spinnerette(sender, receiver, edgeweighting) # Get the network object from the constructor function
#print(nx.info(network)) # Print network description for diganostic purposes

#Get node level metrics
df_centrality = centrality(network) # Get the centrality metrics from the function by supplying the network

influencers_list=[] # initialize a list of top influencer accounts, used for graphing later

print_results_userlevel(df_centrality)

#Network level metrics
print('\nNetwork level metrics\n-------------------------')
print('Number of nodes (accounts):',nx.number_of_nodes(network))
print('Number of edges (mentions between accounts):',nx.number_of_edges(network))
print('Network density (% of possible edges which are extant): ',(nx.density(network))*100,'%',sep='') # this is in % so 100 times higher than standard density
print('Allow retweets:', str(allowRTs))
print('Allow repeated contact:', str(edgeweighting))
print('Remove duplicate tweets:', str(removedups))
print('Allow self loops:', str(selfloop))
print('Number of self loop edges:',nx.number_of_selfloops(network)) # This can be !0 even when the toggle is set to false as sometimes accounts retweet or mention themselves.
if edgeweighting == False:
	print('Transitivity (% of possible triangles which are extant):',nx.transitivity(network))
print('\n')

#print(nx.average_clustering(network)) # this may need an edge weight value which will need to be calculated

#Graphing
influencers_list = [item for sublist in influencers_list for item in sublist] # This flattens the list of influencers
influencers_list = list(dict.fromkeys(influencers_list)) # This removes any duplicates

labeldicto={} # These 3 lines convert the list into a dictonary which is used in the graphing below to label the top influencers. Any account to appear in the top 5 of any of the metrics will have a label.
for account in influencers_list:
	labeldicto.update({str(account):str(account[:15])}) # Only display the first 15 chars of the name. Twitter handles can only be 15 chars long, but if using a hash this makes the graph more readable

nx.draw_networkx(network, alpha=0.7, labels=labeldicto, node_color='#23b7ce', node_size=35, font_size=12, edge_color='#a3a3a3') # Generate the graph
plt.show() # Display the graph
