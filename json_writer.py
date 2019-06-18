textname=[]
for name in set(largest_comp_send+largest_comp_rec):
	textname.append('{"name":"' + name + '"}')
textname = str(textname)
textname = textname.replace("'","")

ref_dic={}
count=0
for each in set(largest_comp_send+largest_comp_rec):
	ref_dic.update({each:count})
	count=count+1

textdetails = []

for send,rec in zip(largest_comp_send,largest_comp_rec):
	textdetails.append('{"source":' + str(ref_dic.get(send)) + ',"target":' + str(ref_dic.get(rec)) + ',"value":' + str(0) + '}')

textdetails=str(textdetails)
textdetails = textdetails.replace("'","")

jsontext = '{"nodes":' + textname + ',"links":' + textdetails + '}'


with open('./Data/data.json', 'w', encoding='1252') as outfile:
    outfile.write(jsontext)
outfile.close()