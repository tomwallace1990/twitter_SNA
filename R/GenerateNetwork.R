library(networkD3)

#Force
datNodes=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\datNodes.csv", header=TRUE)
datLinks=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\datLinks.csv", header=TRUE)

forceNetwork(Links = datLinks, Nodes = datNodes, Source = "source",
             Target = "target", Value = "value", NodeID = "name",
             Group = "group", opacity = 1, zoom =T, bounded = F, opacityNoHover = 1) %>%
  saveNetwork(file = 'C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\R\\Network.html')