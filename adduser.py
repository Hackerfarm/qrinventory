import sys
import random
from pymongo.connection import Connection

con = Connection('localhost', 27017)
db = con["hfinv"]

username=sys.argv[1]
print "Creating user:",username
db.users.insert({"username":username, "url":username+"_"+str(random.randint(0,1e15))})



