#Main
#Tom Wallace
#Created 28/05/2019
#Description: This is a prototype for detecting influencers in twitter data. Given a user and a topic it will user SNA centrality to determine how influential that user is in the given topic network.
# The output is the most influential verified users, the position of the given user, some other verified users positions, a graph, and a sentiment analysis on the network as a whole and the mentions of the given user.

#Done
#	0. Basic functionality - read in data, manage data, build edge list, build network, compute metrics, print metrics
#	2. Self links - toggle to allow or disallow
#	1. Duplicated tweet and bots - set a toggle to allow or disallow them
#	4. Toggle for edge weighting - repeated contact taken into account or not
#	7. Hash usernames to protect identity
#	8. Toggle on/off or mark retweets - do they already do this? added to the searchtwit function in Bluetick.py (now obsolete 29/07/19)
#	13. Deal with capitalisation mismatches
#	11. Identify verified users with API calls and from tweet objects
#	14. Only show non-hashed users
#	12. Switch to be about given username rather than network overall
#	15. Display percentile ranks rather than pure ordered scores because of invariance in scores (particularly in smaller networks)
#	16. Gain control isn't working for people at the bottom (there are no handles below lowly ranked accounts which are below the gain value)
#	17. Isolate the largest component and pass only data on it to R
#	18. Ian suggestion - Sentiment analysis on the corpus to work out if the given user is positive or negative, or topic modelling
#	21. Switch to full text in tweet objects to prevent truncating of text - not a big issue for networking but makes a different for sentiment analysis
#	20. Add cheating - collect all of users tweets which fit the search term and add them to the natural search (removing duplicates and tweets older than oldest search)
#	23. More elegant retweeting toggle with '-filter:retweets' and filter the cheating function
#	22. Add tweets about the given user to cheating
#	19. Ian suggestion - grab network at different time points and compare user position change, extension of 5. Currently compare to last run using txt files to store the results.
#	27. Integrate verified dictionary produced by Verified_users_generator.py

#To do for the future
#	3. Spike detection - automate selection of period, part of rolling input. May be best left to user graphically as in Tracker
#	5. Rolling data input - last 3 days for example, import, process dates, variable to set slice period. can't get tweets older than a week so a week is a good period but depends on how noisy topic is
#	6. Interface/front-end - depends on how this work is integrated into Barrachd systems
#	9. Follower/following networks - should be easy enough to implement - would need another version of edgelister which handles follower/following and a module which grabs this data
#	X. Separate script which searches for mentions about users and does sentiment. Not a feature for this code but would reuse many functions
#	26. application in Barrachd platform
#	26.1 Alerter - bolt on network module, could only run on certain queries so have if rules. wouldn't have to take the users account if check that the given account is verified.
#	26.2 Tracker - brands and business tracking of tweets, social media campaigns
#	26.3 Alerter - system similar to non-parametric heterogeneous graph scan for identifying news about a topic quickly

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
from time import sleep
import random
import scipy.stats as stats
import plotly.plotly as py
import plotly.graph_objs as go
import csv
import subprocess
import webbrowser
from textblob import TextBlob
import os
from datetime import datetime
import math

#####Parameters and settings#####
projectpath = './' # Set the root folder
inputfile = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019.csv' # Manually set the input file
tokenpath = 'C:/Users/Tom Wallace/Dropbox/Stats/twitter_tokens/twitter-api-token_nyetarussian.json' # Tokens for API authentication
random.seed(123456789) # Random is used to select which influential accounts to show after the top 10

selfloop = False # bool. This sets whether to allow self loops, if 'True' tweets with no '@' (someone just tweeting but not mentioning another user) will be added to the edge list as 'author':'author' showing a left link. If 'False' these tweets will be excluded from the edge list
removedups = False # bool. This removes duplicate tweets which are often bots, it looks for identical text content (even from different accounts) but excludes URLs.
edgeweighting_toggle = True # bool. This set whether to allow repeated contact between accounts to be accounted for, SNA analysis usually does not but 'True' is probably best default here
allowRTs = True # bool. Allow retweets or not, will reduce number of tweets imported below value of 'max_tweets' as it filters after the import
hashing_type = 'valid' # cat. 'none', 'full', 'valid' - type of hashing to apply. None: show all usernames. Full: show no usernames. valid: show valid users only (default).
random_depth_gain = 500 # int. This is a gain control for how deep the results printer will look down the list of results, it will need to be larger for smaller networks
max_tweets = 800 # int. How many tweets to request
get_user_activity = False # bool. Get users timeline in addition to normal search, biases network but increases chance of user in results. Useful if topic is large and user is not central to it
getmentions_ofuser = False # bool. Sub option for 'get_user_activity', collections mentions of user, increases bias more but further increases chance of user in network

query = '#DareToCreate' # string. Topic of the request Extinctionrebellion
given_user = 'adidasUK' # string. The input user to return results for greenpeace

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

def getusertweets(tweet_author, tweet_text, searched_tweets, oldest_tweet):
	print('Searching twitter for tweets from the given user (', given_user, '). Please wait...', sep='')
	given_user_tweets = api.user_timeline(screen_name=given_user,count=250,tweet_mode='extended')

	if getmentions_ofuser == True:
		mentions_query = '@' + given_user + ' ' + query
		mentionsofuser = [status for status in tweepy.Cursor(api.search, q=mentions_query, lang='en',tweet_mode='extended').items(250)]
		mentionsofuser = [tweet for tweet in mentionsofuser if given_user.lower() in tweet.full_text.lower() and query.lower() in tweet.full_text.lower()]
		given_user_tweets.extend(mentionsofuser)

	given_user_tweets = [tweet for tweet in given_user_tweets if tweet.id>oldest_tweet] # This filters out tweets from the given user that are older than the oldest tweet collected in the main search
	given_user_tweets = [tweet for tweet in given_user_tweets if tweet.id not in searched_tweets] # Duplicate checking, filter any tweet which is already in searched tweets

	if allowRTs == False:
		given_user_tweets = [tweet for tweet in given_user_tweets if 'RT @' not in tweet.full_text] #remove retweets

	given_user_author = [tweet.user.screen_name for tweet in given_user_tweets]

	given_user_text = gettext_extended(given_user_tweets)

	#This block filters the given user tweets so only ones relevant to the query are kept - this can be sensitive to the formatting of the query
	given_user_tweets_filtered=[]
	given_user_author_filtered=[]
	given_user_text_filtered=[]
	for tweet,author,text in zip(given_user_tweets,given_user_author,given_user_text):
		if query.lower() in text.lower(): # force bother lower case to increase compatability
			given_user_tweets_filtered.append(tweet)
			given_user_author_filtered.append(author)
			given_user_text_filtered.append(text)

	searched_tweets.extend(given_user_tweets_filtered)
	tweet_author.extend(given_user_author_filtered)
	tweet_text.extend(given_user_text_filtered)

	return tweet_author, tweet_text, searched_tweets #return the filtered tweets for the given user - they still may get kicked out if none of theses tweets have an @

def searchtwit(max_tweets, allowRTs,get_user_activity):
	print('Searching twitter for ', max_tweets, ' tweets on the topic "', query, '". Please wait...', sep='')
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

def removeduplicates(tweets):
	urlmatch = re.compile(r'(https|http)://([^\s]+)')
	tweets = [re.sub(r'(https|http)://([^\s]+)', 'URL', tweet) for tweet in tweets]
	lentweet = len(tweets)
	tweets = set(tweets)
	#print('N.B.',lentweet-len(tweets), 'of',lentweet ,'tweets removed as duplicates.')

	return tweets

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

def hasher (sender, receiver, hashing_type, valid_dict, given_user):
	if hashing_type == 'valid':
		sender = [hashlib.sha224(handle.encode()).hexdigest() if valid_dict.get(handle)!=True and handle != given_user else handle for handle in sender] # Hash it unless it's valid or the given user
		receiver = [hashlib.sha224(handle.encode()).hexdigest() if valid_dict.get(handle)!=True and handle != given_user else handle for handle in receiver]
	elif hashing_type == 'full':
		sender = [hashlib.sha224(handle.encode()).hexdigest() if handle != given_user else handle for handle in sender]
		receiver = [hashlib.sha224(handle.encode()).hexdigest() if handle != given_user else handle for handle in receiver]
	elif hashing_type == 'none':
		pass

	return sender, receiver

def edgecounter(senders, receivers, edgeweighting_toggle):
	if edgeweighting_toggle == True:

		dyads = [send+';'+rec for send,rec in zip(senders, receivers)]

		edge_weights = []

		for dyad in dyads:
			number_of_dyads = re.findall(dyad, str(dyads))
			edge_weights.append(len(number_of_dyads))

		return edge_weights

def spinnerette(senders, receivers, edgeweighting_toggle=False):
	# This function takes in an edge list as a sender and receiver list (as produced by edgelister) and converts them into a network object from the library networkx

	if edgeweighting_toggle == True:
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

def print_results_userlevel(result_list, id_list, random_depth_gain):
	# This print function is a bit complex but basically it prints the sequential top 10, then the given user account, then 9 random accounts ranked lower than the user account - 20 results total
	# That is unless the given user account is in the top 10, then it prints the top results in order until it hits the uder account, then it prints the user accout and then random accounts until it hits 20 in total

	#Get the variables from the function head
	result_centrality = result_list
	index_list = id_list
	
	#Ths block gets the slice position of the given account by incrimenting a counter until it finds the given user
	given_user_counter=0
	if given_user in index_list:
		for handle in index_list:
			if handle!=given_user:
				given_user_counter=given_user_counter+1
			else:
				break
	else:
		print('WARN: Given user not found in network. Quiting.')
		quit()
	
	percentile_list = [stats.percentileofscore(result_centrality, item, kind='rank') for item in result_centrality]

	#Get a list from 1 to the max used to show user position
	counter_list = list(range(1,len(index_list)+1))

	random_depth_gain = random_depth_gain/(percentile_list[given_user_counter]**2)

	print('You are more prominent than (or at least as prominent as) ', '%.1f' % percentile_list[given_user_counter], '% of users in this network!', sep='')
	
	#This chunk of code loads a text file contianing the result last time, prints it and the difference between it and now
	#It then saves the current result to the textfile, overwriting it.
	#If it doesn't find a file (first run) it skips the printing and makes the file
	if os.path.isfile(previous_data_path + 'last_time_userlevel.txt'):
		file = open(previous_data_path + 'last_time_userlevel.txt', 'r')
		percentile_last_time = file.read()
		print('Your prominence last time was ', '%.1f' % float(percentile_last_time), ', this is a difference of ', '%.1f' % (percentile_list[given_user_counter]-float(percentile_last_time)), '%', sep='')
	with open(previous_data_path + 'last_time_userlevel.txt', 'w') as file:
		file.write(str(percentile_list[given_user_counter]))

	print("\nHere's how some verified public accounts scored")
	previous_result = []
	random_list = [random.uniform(0, 1) for each in index_list]
	result_count=1
	for handle,result,rando,position in zip(index_list,result_centrality,random_list,percentile_list):
		if len(handle) < 56 and handle!=given_user:
			if result_count > 10:
				continue
			print('\tRank: ','%.1f' % position, '% \tScore: ', '%.4f' % result, '\tUser: ', handle, sep='')
			result_count=result_count+1
			previous_result.append(handle)
		elif handle==given_user:
			print('\n--------------------------------------------------------------------')
			print('\tRank: ','%.1f' % position, '% \tScore: ', '%.4f' % result, '\tYou are here! (Your handle: ', handle, ')', sep='')
			print('--------------------------------------------------------------------\n')
			result_count=result_count+1
			previous_result.append(handle)
			given_user_pos = position
	for handle,result,rando,position in zip(index_list,result_centrality,random_list,percentile_list):	
		if given_user in previous_result and handle not in previous_result and position<=given_user_pos and len(handle) < 56 and rando < (random_depth_gain):
			print('\tRank: ','%.1f' % position, '% \tScore: ', '%.4f' % result, '\tUser: ', handle, sep='')
			result_count=result_count+1
			if result_count > 20:
				break

def print_results_network(netowrk,searched_tweets):
	print('Number of nodes (accounts):',nx.number_of_nodes(network))
	print('Number of edges (mentions between accounts):',nx.number_of_edges(network))
	print('Network density (% of possible edges which are extant): ',(nx.density(network))*100,'%',sep='') # this is in % so 100 times higher than standard density
	print('Newest tweet sent at:',searched_tweets[0].created_at)
	print('Oldest tweet sent at:',searched_tweets[-1].created_at)
	print('Allow retweets:', str(allowRTs))
	print('Allow repeated contact:', str(edgeweighting_toggle))
	print('Remove duplicate tweets:', str(removedups))
	print('Allow self loops:', str(selfloop))
	print('Number of self loop edges:',nx.number_of_selfloops(network)) # This can be !0 even when the toggle is set to false as sometimes accounts retweet or mention themselves.
	print('Get user activtiy:',str(get_user_activity))
	if edgeweighting_toggle == False:
		print('Transitivity (% of possible triangles which are extant):',nx.transitivity(network))
	print('\n')

	#Previous network stats
	if os.path.isfile(previous_data_path + 'last_time_overall.txt'):
		file = open(previous_data_path + 'last_time_overall.txt', 'r')
		last_run_data = file.read().split(',')
		print('In the previous network...\n-------------------------')
		print('The number of nodes was:', last_run_data[0], 'a difference of', nx.number_of_nodes(network)-int(last_run_data[0]))
		print('The number of edges was:', last_run_data[1], 'a difference of', nx.number_of_edges(network)-int(last_run_data[1]))
		print('The density was:', last_run_data[2], 'a difference of', ((nx.density(network))*100)-float(last_run_data[2]))
		print('\n')
	with open(previous_data_path + 'last_time_overall.txt', 'w') as file:
		file.write(str(nx.number_of_nodes(network)))
		file.write(',')
		file.write(str(nx.number_of_edges(network)))
		file.write(',')
		file.write(str((nx.density(network))*100))

def simplegraphing(sender,receiver, influencers_list):
	influencers_list = [item for sublist in influencers_list for item in sublist] # This flattens the list of influencers
	influencers_list = list(dict.fromkeys(influencers_list)) # This removes any duplicates

	influencers_list=[given_user]

	labeldicto={} # These 3 lines convert the list into a dictonary which is used in the graphing below to label the top influencers. Any account to appear in the top 5 of any of the metrics will have a label.
	for account in influencers_list:
		labeldicto.update({str(account):str(account[:15])}) # Only display the first 15 chars of the name. Twitter handles can only be 15 chars long, but if using a hash this makes the graph more readable

	nodelist = (list(set(sender+receiver)))

	colour_list=[]
	size_list=[]
	for node in nodelist:
		if node==given_user:
			colour_list.append('#FF0000')
			size_list.append(250)
		else:
			colour_list.append('#23b7ce')
			size_list.append(35)

	nx.draw_networkx(network, alpha=0.7, nodelist=nodelist, labels=labeldicto, node_color=colour_list, node_size=size_list, font_size=12, edge_color='#a3a3a3') # Generate the graph
	plt.show() # Display the graph

def htmlgraph(network, sender, receiver, edgeweighting_toggle=False):
	network_undir = network.to_undirected()

	#subgraphs = list(nx.connected_component_subgraphs(network_undir))
	set_largest_comp = max(nx.connected_components(network_undir), key=len)
	#set_largest_comp = nx.connected_components(network_undir)

	largest_comp_send = [handle for handle in sender if handle in set_largest_comp or handle in given_user]
	largest_comp_rec = [handle for handle in receiver if handle in set_largest_comp or handle in given_user]

	edge_weights = edgecounter(largest_comp_send, largest_comp_rec, edgeweighting_toggle)

	unique_set = list(set(largest_comp_send+largest_comp_rec))
	unique_set.sort()
	nodes_exp = unique_set # all handles including hashed ones
	nodes_exp_blanked = []
	for node in nodes_exp: # This block writes an empty space for hashes users so they don't show up on the netowrk graph
		if len(node) > 50:
			nodes_exp_blanked.append(' ')
		else:
			nodes_exp_blanked.append(node) # authenticated users can show up
	nodes_exp = nodes_exp_blanked

	#group_exp = [1 for each in unique_set] # this just sets group to 1 for all
	group_exp=[]
	for each in unique_set: # This sets the user groups, 2 for hashed users, 1 for valid, and 3 for the given user
		if len(each) > 50: # Hashed users identified by having names longer than 50 chars, twitter handles can't be that long.
			group_exp.append(2)
		elif each == given_user:
			group_exp.append(3)
		else:
			group_exp.append(1)

	size_exp = [10 for each in unique_set] # size based on percentile rank?

	export_data = zip(nodes_exp,group_exp,size_exp)
	output = './Data/datNodes.csv' # This writes the node data out
	with open(output, 'w', encoding='1252', errors='replace', newline='') as file:
		wr = csv.writer(file)
		wr.writerow(('name', 'group', 'size'))
		wr.writerows(export_data)
	file.close()

	ref_dic={}
	count=0
	for each in unique_set: # Give each handle a unique number
		ref_dic.update({each:count})
		count=count+1

	send_exp = []
	rec_exp = []

	for send,rec in zip(largest_comp_send,largest_comp_rec): # Replace the handles with numbers for R
		send_exp.append(ref_dic.get(send)) 
		rec_exp.append(ref_dic.get(rec))

	#value_exp = [1 for each in send_exp] # value based on edge weight - will need to calc it
	value_exp = edge_weights # value by edge weights, from function

	export_data = zip(send_exp,rec_exp,value_exp)
	output = './Data/datLinks.csv' # Write the links data out
	with open(output, 'w', encoding='1252', errors='replace', newline='') as file:
		wr = csv.writer(file)
		wr.writerow(('source', 'target', 'value'))
		wr.writerows(export_data)
	file.close()

	#R graph - call the R file
	subprocess.call(['C:/Program Files/R/R-3.6.0/bin/Rscript.exe', '--vanilla', './R/GenerateNetwork.R'], shell=True)

	#Edit the HTML - this block uses regex to change one variable in the HTML to disable the mouseover behaviour
	network_on_disk_html = "./R/Network.html" # Location of HTML graph on disk
	HTMLfile = open(network_on_disk_html, 'r')
	HTMLtext = HTMLfile.read() # Read in HTML as text
	#var unfocusDivisor = 4; # this is the varaible that needs changed 4 > 1
	HTMLtext = re.sub('(?<=var unfocusDivisor = )\d(?=;)','1',HTMLtext) # Change the var with regex
	with open("./R/Network_fixed.html",'w') as output:
		output.write(HTMLtext) # Wrtie the HTMLP backout as text

	#Open the HTML graph R generates
	new = 2 # open in a new tab
	full_path = (os.path.dirname(os.path.realpath(__file__))) # Browser needs a full path - get the path of this script
	
	url = full_path+"/R/Network_fixed.html" # combine script path to locate network
	webbrowser.open(url,new=new) # Open the edited HTML

def sentiment_analysis(corpus,removedups):
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

################################################################################
################################## Main ########################################
################################################################################
#Authenticate via public API
api = athenticate(tokenpath)

#Grab tweets on given topic from API. Account is list of senders, corpus is matching list of tweet text, searched_tweets is matching list of the full tweet objects
account, corpus, searched_tweets = searchtwit(max_tweets, allowRTs,get_user_activity)

#Case conversion
account = [text.lower() for text in account]
corpus = [text.lower() for text in corpus]
given_user=given_user.lower()

if removedups == True:
	corpus = removeduplicates(corpus) # how does this not unbalance the lists? check!

#Create edge list
sender, receiver = edgelister(account, corpus, selfloop, removedups) # Call the edgelister function to convert the authors and tweets into an edge list
	# to save the data as an edge list, include an output path as option 3 above such as outputpath = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019UTF8_edgelist.csv' 
	# Sender and receiver are not equal length lists showing the asymmetric links

#Validation - prevalidate (get validation from existing tweet objects)
	#Pre validation uses infrom from the already downloaded tweet objects and saves making unnessiary API calls. It reduces the number of calls by more than 90%
valid_dict = {}
all_handles = (list(set(sender+receiver)))
valid_dict = validate(valid_dict, all_handles)

#Check given account is in network
if given_user not in sender and given_user not in receiver:
	print('>>> WARN: The given handle is not in the network which was collected, try altering query <<<\nExiting.')
	quit()

#Remove invalid user names
invalid = [handle for handle in (list(set(sender+receiver))) if valid_dict.get(handle)==None] # It is possible to tweet at an invalid handle, these are picked up as part of primevalidate and removed here (only handles in primevalidate are picked up)

for send, rec in zip(sender,receiver): # for each dyadic edge
	for inval in invalid: # for each invalid handle
		if inval in send: #if either part of the dyad is invalid remove the whole dyad
			sender.remove(send)
		if inval in rec:
			receiver.remove(rec)

#Hash usernames
sender, receiver = hasher(sender, receiver, hashing_type, valid_dict, given_user)

#Create network
network = spinnerette(sender, receiver, edgeweighting_toggle) # Get the network object from the constructor function
#print(nx.info(network)) # Print network description for diagnostic purposes

#Get node level metrics
df_centrality = centrality(network) # Get the centrality metrics from the function by supplying the network

influencers_list=[] # initialize a list of top influencer accounts, used for graphing later

### Setting up the last time file
current_time = datetime.now()
previous_data_path = './Previous_data/'
if not os.path.exists(previous_data_path): # If the path doesn't exist, make it
	os.makedirs(previous_data_path)

print('Network collection finished at (current time):', current_time)
if os.path.isfile(previous_data_path + 'last_time_date.txt'):
	file = open(previous_data_path + 'last_time_date.txt', 'r')
	last_run_timedate = file.read()
	print('Pervious data was collected at:', last_run_timedate)
with open(previous_data_path + 'last_time_date.txt', 'w') as file:
	file.write(str(current_time))

#### Print results
print('\n====================================\nYou in the network\n====================================')
df_centrality['Combined_cent'] = df_centrality['degree'] + df_centrality['closeness'] + df_centrality['eigenvector']
#df_centrality['Combined_cent'] = df_centrality['eigenvector']
df_centrality = df_centrality.sort_values(by=['Combined_cent'],ascending=False)

test_results = list(df_centrality['Combined_cent'])
index_list = list(df_centrality.index.tolist())

print_results_userlevel(test_results,index_list,random_depth_gain)
print('\n')

#### Network level metrics
print('====================================\nNetwork level metrics\n====================================')
print_results_network(network,searched_tweets)

#### Simplistic Graphing - not great
#simplegraphing(sender,receiver, influencers_list)

#### HTML interactive Graphing 2 - Looks good but not very customizable, could be better if passed to the module in javascript and not the R wrapper
htmlgraph(network, sender, receiver, edgeweighting_toggle)

#### Sentiment analysis
#Network overall
print('====================================\nSentiment analysis\n====================================')
print('Sentiment scores range between -1 (very negative) and 1 (very positive).\n')

sentiment, number_of_tweets, example, sd = sentiment_analysis(corpus, removedups) # get the sentiment
print('The sentiment for the whole network is:', sentiment, 'based on', number_of_tweets, 'tweets with a polarity of',sd)
print('This indicates', english_sentiment(sentiment),'sentiment.')
print('_______________________________________________________________________\nExample of an average sentiment tweet: "',example,'"\n_______________________________________________________________________\n', sep='')

#Mentions of given user
corpus = [tweet for tweet in corpus if '@'+given_user+' ' in tweet] # keep just tweets about the given user
if corpus==[]:
	print('There were no mentions of the given user, all of thier links were outbound.')
	quit()
sentiment_user, number_of_tweets, example, sd = sentiment_analysis(corpus, removedups) # get the sentiment
print('\nThe sentiment for mentions of the given user is:', sentiment_user, 'based on', number_of_tweets, 'tweets with a polarity of',sd)
print('This indicates', english_sentiment(sentiment_user),'sentiment.')
print('_______________________________________________________________________\nExample of an average sentiment tweet: "',example,'"\n_______________________________________________________________________\n', sep='')

#Comparison for sentiment
if os.path.isfile(previous_data_path + 'last_time_sentiment.txt'):
	file = open(previous_data_path + 'last_time_sentiment.txt', 'r')
	last_run_data = file.read().split(',')
	print('In the previous network the overall sentiment was:', last_run_data[0], 'a difference of', sentiment-float(last_run_data[0]))
	print('In the previous network the sentiment of mentions of give user was:', last_run_data[1], 'a difference of', sentiment_user-float(last_run_data[1]))
with open(previous_data_path + 'last_time_sentiment.txt', 'w') as file:
	file.write(str(sentiment))
	file.write(',')
	file.write(str(sentiment_user))
