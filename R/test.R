##############################################################################
############################ Import edgelist in R ############################ 
##############################################################################
#Tom Wallace
#13/11/18

#Clear
rm(list = ls())

#load packages network, sna, and ergm, set PRG seed
#install.packages('coda')
#install.packages('latticeExtra')
#install.packages('statnet')
#install.packages('sna')
#install.packages("igraph")
#install.packages("ergm")
#install.packages("networkD3")
#install.packages("magrittr")
 

library(latticeExtra)
library(coda)
library(statnet)
library(igraph)
library(sna)
library(networkD3)
library(magrittr)

set.seed(12345)

###### Statnet ######
#Import edgelist into statnet http://www.shizukalab.com/toolkits/sna/sna_data
el=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\Extinction rebellion\\extinction rebellion30052019_edgelistR.csv",header=T)
el[,1]=as.character(el[,1])
el[,2]=as.character(el[,2])
net_network1=network(el,matrix.type="edgelist",directed=TRUE) 

#Summarise network
net_network1

network.density(net_network1)

###### iGraph ######
#Import
netdat=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\Extinction rebellion\\extinction rebellion30052019_edgelistR.csv", header=TRUE)
graph1=graph.data.frame(netdat,directed=FALSE)

#Duplicate edges handling in iGraph #http://igraph.org/r/doc/simplify.html
is_simple(graph1)
graph1simple = simplify(graph1, remove.multiple = TRUE, remove.loops = TRUE, edge.attr.comb = "sum")
is_simple(graph1simple)

#Number of nodes (order) and edges (size)
gorder(graph1) # same as statnet
gsize(graph1)

gorder(graph1simple)
gsize(graph1simple)

##### Plotting ##### 
par("mar")
par(mar=c(1,1,1,1))

plot.network(net_network1, displaylabels=F, boxed.labels=F, main="Hairball!") # Unusable

#networkD3
netdat=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\Extinction rebellion\\extinction rebellion30052019_edgelistR.csv", header=TRUE)

graph_d3 <- netdat

graph_d3 <- igraph_to_networkD3(graph1)

simpleNetwork(graph_d3, zoom=TRUE)

#Force
datNodes=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\datNodes.csv", header=TRUE)
datLinks=read.csv("C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\Data\\datLinks.csv", header=TRUE)

forceNetwork(Links = datLinks, Nodes = datNodes, Source = "source",
             Target = "target", Value = "value", NodeID = "name",
             Group = "group", opacity = 1, zoom =T, bounded = F, opacityNoHover = 0.4) %>%
  saveNetwork(file = 'C:\\Users\\Tom Wallace\\Dropbox\\2PostyGrady_theReturn\\Internship\\twitter_SNA\\R\\Net1.html')



#http://www.biofabric.org/gallery/pages/SuperQuickBioFabric.html
#https://stackoverflow.com/questions/22453273/how-to-visualize-a-large-network-in-r

c_g <- fastgreedy.community(graph1simple)
res_g <- simplify(contract(graph1simple, membership(c_g)))

plot(res_g)