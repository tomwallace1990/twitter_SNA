#Main
#Tom Wallace
#Created 28/05/2019
#Description: This is a prototype for detecting influencers in twitter data.

#To do:
#	1. Duplicated tweet and bots - set a toggle to allow or disallow them
#	2. Self links - toggle to allow or disallow - currenrly disallowed
#	3. Spike detection - automate selection of preiod

#####Imports#####
import pandas as pd
import re
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt

#####Functions#####

def edgelister(authors, tweets, sav_path=None): 
# This function takes tweet objects and generates an edgelist, which is a pair of equal length lists showing the sender and receiver of each tweet which contains one or more '@'
# Where there is more than one '@' in a tweet an equal number of lines is created in the edge list
# This function expects a list of string handles and a matching list of tweet text.
# Example: the tweet 'hi, this is a test @test @testing' by account tomw would result in the lists - [tomw, tomw] [test, testing] 
	
	sender, receiver=[], []

	for tweet, author in zip(corpus, account): # Need to do a zip loop to keep author linked to the right tweet
		links = re.findall(r'(?<=@)\w+', tweet) # Use regex to find the block of characters folliwng the @ symbol which is the receiving handle
		if len(links) > 0: # This checks if an @ was actually found, if not it moves back to the start of the loop
			for link in links: # There is often more than one @ in a tweet, this ensures they are all captured
				sender.append(author) # The sender is the author of the tweet
				receiver.append(link) # The receiver is each handle after the @
	
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

def spinnerette(senders, receivers):
# This function takes in an edge list as a sender and receiver list (as produced by edgelister) and converts them into a network object from the library networkx

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

#####Main#####
projectpath = './' # Set the root folder

inputfile = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019.csv' # Manually set the input file
#inputfile = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019dup.csv' # Manually set the input file

df_in = pd.read_csv(inputfile) # Read the input file into a data frame

for value in ['Source', 'Time Posted', 'Location', 'Klout', 'Follow']: # Drop unneeded columns
	df_in.drop(columns=[value], inplace=True)

account = df_in['Account'].tolist() # Get the senders of each tweet as a list
corpus = df_in['Content'].tolist() # Gte content of each tweet as a list

sender, receiver = edgelister(account, corpus) # Call the edgelister function to convert the authors and tweets into an edge list
# to save the data as an edge list, include an output path as option 3 abvoe such as outputpath = projectpath + '/Data/Extinction rebellion/' + 'extinction rebellion spike 12.04.2019 to 02.05.2019UTF8_edgelist.csv' 
# Sender and receiver are not equal length lists showing the asymmetric links

network = spinnerette(sender, receiver) # Get the network object from the constructor function

df_centrality = centrality(network) # Get the centrality metrics from the function by supplying the network
print(df_centrality) # show the data frame - it could also be written out as a CSV for manual processing

df_centrality_width = df_centrality.shape # Get the width of the dataframe as an int - it is used in the loop below. Width is the number of columns/ number of metrics which were calculated
colnames = list(df_centrality.columns.values) # Get the headers from the data frame so they can be used in the output below - they are set in the centrality function

influencers_list=[] # initialize a list of top influencer accounts, used for graphing later

print('\n\nMost influential accounts\n-------------------------')
for label,value in zip(colnames, range(0,df_centrality_width[1])): # this loop takes each of the metrics in turn and prints the top 5 accounts for each metric. Effecitvely this is the mian results output
	series_results = df_centrality[df_centrality.columns[value]] # Create a temp series by slicing into the dataframe with the value iterator
	series_results_sort = series_results.sort_values(ascending=False) # reverse sort the temp seires so the top influencers are at the top
	print(value, '. Top five influential accounts based on ', label, ' centrality.', sep='') #Print a header with the column name for info
	if series_results.sum() == 0: # This if checks if the seires has valid results, if not it will print a warning instead.
		print('>>>WARN: Results are all naught. The network may be too small/simple to calculate this metric. <<<')
	else:
		print(series_results_sort[:5]) # If it is valid the top 5 influencers will be printed
		influencers = list(series_results_sort[:5].index) # These two lines are used for the graphing below, they add the names of the top 5 influencers to a list
		influencers_list.append(influencers)
	print('\n')

#Graphing
influencers_list = [item for sublist in influencers_list for item in sublist] # This flattens the list of influencers
influencers_list = list(dict.fromkeys(influencers_list)) # This removes any duplicates

labeldicto={} # These 3 lines convert the list into a dictonary which is used in the graphing below to label the top influencers. Any account to appear in the top 5 of any of the metrics will have a label.
for account in influencers_list:
	labeldicto.update({str(account):str(account)})

nx.draw_networkx(network, alpha=0.7, labels=labeldicto) # Generate the graph
#plt.show() # Display the graph 
