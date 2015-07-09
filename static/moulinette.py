s=open("labels65.svg").read()

f=True
ind = 0
r=""
i=0
for ss in s.split("{1}"):
	r+=ss+"{"+str(i)+"}"
	i=i+1

print r[:-4]
