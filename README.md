# twitter_SNA

## Description
This repo is for the code and other materials I develop for my MSc dissertation project. The project takes the form of an internship with the company Barrachd and focuses on identifying influential actors in Twitter networks.

## Scripts
Network_analyser.py - This is the primary script, it takes in a Twitter username and topic and produces a ranking of prominence in the network formed by the topic. It also produces a graph and performs a sentiment analysis.

Topic_modeller.py - This script sits before Network_analyser.py and takes in just a Twitter username. It returns the top hashtags and topics tweeted about by the user.

Verified_users_generator.py - This script solves the problem of avoiding profiling individual Twitter users by building a dictionary of all verified users which can be accessed by the other scripts.

## Other files
valid_screennames.json - JSON dictionary of all verified Twitter users, produced by Verified_users_generator.py.

Workbook.xlsx - the project workbook with day-by-day progress notes.

## Directories
Data\Valid_twitter_handles - Error files and temp files produced by .Verified_users_generator.py
Frontend mockup - Mockup of how the scripts might look in practise.
Previous_run_data - txt files created by Network_analyser.py to record the results of the last run and compare them to the current run.
R - files and R script for the network generator used in Network_analyser.py.