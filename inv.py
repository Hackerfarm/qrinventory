#!/usr/bin/env python
# -*- coding: utf-8

from datetime import datetime
from pymongo.connection import Connection
from qrtools import QR
import gridfs

from bson.objectid import ObjectId
 
import os.path
import tornado.auth
import tornado.template
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import time
import StringIO
import Image
import random

from markdown import markdown

from tornado.options import define, options

import config

template_object_edit = u"""
<form enctype="multipart/form-data" method="POST" action="/newobject" id="newobjform">
{secure_cookie}
<input type="hidden" value="{object_id}" name="url_id"/>
<div>
	<span>Description (Japanese)</span>
	<span><input class="text" name="description_jp" value={description_jp}></input></span>
</div>
<div>
	<span>Description (English)</span>
	<span><input type="text" name="description_en" value={description_en}></input></span>
</div>
<div>
	<span>Owner</span>
	<span><input type="text" name="owner" value={owner}></input></span>
</div>
<div>
	<span>Take a picture of the tool:</span>
	<span><input type="file" accept="image/*;capture=camera" name="pic"></span>
</div>
<div>
	<span>Current location of the tool</span>
	<span>
		<select name="location" onclick="
					if(value=='Other'){{
						document.getElementById('newlocation').style.visibility='visible';
					}}
					else {{
						document.getElementById('newlocation').style.visibility='hidden';
					}}">
			{locationlist}
			<option>Other</option>
		</select>
	</span>
</div>
<div id="newlocation" style="visibility:hidden">Please enter the name of the new location: <input name="newlocationname"></div>
	<!-- <span class="main_button">Locate through GPS</span> -->

</form>
<div onmousedown="document.getElementById('newobjform').submit()" class="main_button">Create new tool</div>"""

def header(handler):
		handler.write(
"""<link href="/static/style.css" rel="stylesheet" class="text/css">
<div class="header"><a href="/">Back to list</a></div>""")

def generate_locations_list(db):
	locations = db.locations.find()
	s_locations = ""
	first = True
	for l in locations:
		if first:
			s_locations+="<option>{0}</option selected='selected'>\n".format(l["name"])
			first=False
		else:
			s_locations+="<option>{0}</option>\n".format(l["name"])
	return s_locations

def generate_actions_list(db, objid):
	actions = db.actions.find({"object_id":objid})
	s_acts = ""
	acts = list()
	for a in actions:
		acts.append(a)
	acts.sort(key=(lambda x:x["timestamp"]))
	for a in acts:
		s_acts+=u"<div>At {time}, {user} did {action} to {location}</div>\n".format(user = a["user"],
		                                                                      time = a["timestamp"],
		                                                                      action = a["action"],
		                                                                      location = a["location"])
	return s_acts



class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("hfinv_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):
	def get(self):
		header(self)
		self.write("""
		<div class="title">Welcome, {0}</div>
		<div class="main_button" onmousedown="document.location = '/list'">View tools list</div>
		""".format(self.get_current_user()))

class ListHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		header(self)
		self.write("""
		<div class="title">Welcome, {0}</div>
		<div class="list">List</div>
		""".format(self.get_current_user()))
		db = self.application.database
		for tool in db.tools.find():
			if tool.has_key("thumbnail_id"):
				imgid = tool["thumbnail_id"]
			else:
				imgid = tool["picture_id"]
			self.write("""<div class='tool_list_element'>
						<a href='/o/{link}'>
						<div><img width="150px" height="150px" src='/p/{img}'></div>
						<div class='tool_list_name'>{name}</div></a>
					</div>""".format(
						link=str(tool["url_id"]),
						img=str(imgid),
						name=tool["description_en"])
						)


class EditObjectHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, path):
		header(self)
		db = self.application.database
		results = db.tools.find({'url_id':path})
		if results.count()==0:
			self.write(template_object_edit.format(
			            secure_cookie=self.xsrf_form_html(), 
			            object_id=path,
			            description_jp="",
			            description_en="",
						locationlist=generate_locations_list(db),
			            owner=""))
		else:
			db = self.application.database
			tool = db.tools.find_one({'url_id':path})
			self.write(template_object_edit.format(
			           description_en=tool.get("description_en",""),
			           description_jp=tool.get("description_jp",""),
			           location=tool.get("location",""),
			           owner=tool["owner"],
			           img_url=str(tool["picture_id"]),
			           object_id=path,
						locationlist=generate_locations_list(db),
			           secure_cookie=self.xsrf_form_html()))
	def put(self,path):
		return

class QRHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, path):
		header(self)
		db = self.application.database
		results = db.tools.find({'url_id':path})
		if results.count()==0:
			self.write(template_object_edit.format(
						secure_cookie=self.xsrf_form_html(), 
						object_id=path,
						description_jp="",
						description_en="",
						locationlist=generate_locations_list(db),
						owner=""))
		else:
			db = self.application.database
			tool = db.tools.find_one({'url_id':path})
			self.write(u"""
			<div id="description_en">{description_en}</div>
			<div id="description_jp">{description_jp}</div>
			<div id="location">Location: {location}</div>
			<div id="owner">Owner: {owner}</div>
			<div id=image"><a href="/p/{img_url}">
				<img width = "300px" height="300px" src="/p/{img_url}"></a>
			</div>
			<div class="main_button">
				<a href="/os?action=borrowing&object_id={object_id}">I am borrowing this object</a>
			</div><br/>
			<div class="main_button">
				<a href="/os?action=returning&object_id={object_id}">I am returning this object</a>
			</div><br/>
			<div class="main_button">
				<a href="/os?action=found&object_id={object_id}">I found this object</a>
			</div><br/>
			<div class="main_button">
				<a href="/edit/{object_id}">Edit this object</a>
			</div>
			<div class="actions_list"><b>Last actions</b>
			{actionslist}
			</div>
			""".format(description_en=tool.get("description_en",""),
			           description_jp=tool.get("description_jp",""),
			           location=tool.get("location",""),
			           owner=tool["owner"],
			           img_url=str(tool["picture_id"]),
			           object_id=path,
			           actionslist=generate_actions_list(db, path)))

class ObjectStatusHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		header(self)
		db = self.application.database
		act = self.request.arguments.get("action",[""])[0]
		if act=="found":
			msg ="I found this object at :"
		elif act=="borrowing":
			msg ="I am borrowing this object. It will be at :"
		else:
			msg ="I returned this object. It is now at:"
		self.write(u"""
		<div class="status_msg">{msg}</div>
		<form action="/os" method="POST">
			<input type="hidden" name="object_id" value="{object_id}"/>
			<input type="hidden" name="action" value="{action}"/>
		<select name="location" onclick="
					if(value=='Other'){{
						document.getElementById('newlocation').style.visibility='visible';
					}}
					else {{
						document.getElementById('newlocation').style.visibility='hidden';
					}}">
			{locationlist}
			<option>Other</option>
		</select>
		<div id="newlocation" style="visibility:hidden">Please enter the name of the new location: <input name="newlocationname"></div>
			<input type="submit" value="Validate"/>
			{secure}
		</form>""".format(object_id = self.request.arguments.get("object_id",[""])[0],
		                  action = self.request.arguments.get("action",[""])[0],
		                  msg = msg,
		                  secure=self.xsrf_form_html(),
		                  locationlist=generate_locations_list(db)))
	@tornado.web.authenticated
	def post(self):
		header(self)
		self.write(self.request.arguments.get("location", [""])[0])
		db = self.application.database
		loc = self.request.arguments.get("location", [""])[0]
		if(loc=="Other"):
			loc = self.request.arguments.get("newlocationname", [""])[0]
			if db.locations.find({"name":loc}).count()==0:
				db.locations.insert({"name":loc})
		db.actions.insert({
			"action":self.request.arguments.get("action",[""])[0],
			"user":self.get_current_user(),
			"location":loc,
			"timestamp":datetime.now(),
			"object_id":self.request.arguments.get("object_id",[""])[0]})
		db.tools.update({"url_id":self.request.arguments.get("object_id",[""])[0]},
		                 {"$set": {"location": self.request.arguments.get("location",[""])[0]}})


class NewObjHandler(BaseHandler):
	@tornado.web.authenticated
	def post(self):
		header(self)
		self.write("What do I get?<br>"+str(self.request.files['pic'][0]['filename']))
		fs = self.application.gridfs
		db = self.application.database
		imgid = fs.put(StringIO.StringIO(self.request.files['pic'][0]['body']))
		thb = Image.open(StringIO.StringIO(self.request.files['pic'][0]['body']))
		thb.thumbnail((128,128), Image.ANTIALIAS)
		output = StringIO.StringIO()
		thb.save(output, format="JPEG")
		thbid = fs.put(output.getvalue())

		loc = self.request.arguments.get("location", [""])[0]
		if(loc=="Other"):
			loc = self.request.arguments.get("newlocationname", [""])[0]
			if db.locations.find({"name":loc}).count()==0:
				db.locations.insert({"name":loc})

		newtool = {
		'owner': self.request.arguments.get("owner",[""])[0],
		'url_id': self.request.arguments.get("url_id")[0],
		'description_jp': self.request.arguments.get("description_jp", [""])[0],
		'description_en': self.request.arguments.get("description_en", [""])[0],
		'picture_id': imgid,
		'thumbnail_id': thbid,
		'location': loc}
		db.tools.insert(newtool)
		
				
		self.write("<img src='/p/{0}'>".format(str(imgid)))

class UploadPicHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		header(self)
		self.write("""
		<form enctype="multipart/form-data" method="POST" action="/uploadpicture">
			<input type="file" accept="image/*;capture=camera" name="pic">
			<input type="hidden" name="pouic" value="1">
			<input type="submit">
		</form> """)
		
	@tornado.web.authenticated
	def post(self):
		header(self)
		self.write("What do I get?<br>"+str(self.request.files['pic'][0]['filename']))
		img = Image.open(StringIO.StringIO(self.request.files['pic'][0]['body']))
		img.save("./a", img.format)
		fs = self.application.gridfs
		db = self.application.database
		imgid = fs.put(StringIO.StringIO(self.request.files['pic'][0]['body']))
		self.write(str(imgid))
		#db.dev.insert({'imgid': imgid })


class PictureHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.get("")
		
	@tornado.web.authenticated
	def get(self, path):
		self.set_header("Content-Type", "image/jpeg")
		fs = self.application.gridfs
		db = self.application.database
		#imgid = db.dev.find_one({"imgid":{'$exists':True}})
		#self.write(fs.get(imgid["imgid"]).read())
		self.write(fs.get(ObjectId(path)).read())

class GenerateQRHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.get("")
		
	@tornado.web.authenticated
	def get(self, path):
		try:
			if(str(int(path))!=path):
				self.write("Incorect ID")
				return
		except:
			self.write("Incorect ID")
			return
		home_url = options.home_url
		if home_url.startswith("http://"):
			home_url = home_url[7:]
		q=QR(u""+home_url+"/o/"+path)
		q.encode()
		self.set_header("Content-Type", "image/gif")
		self.write(open(q.filename).read())

class Generate44QRHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		db = self.application.database
		self.write("<table>\n  <tr>\n")
		for i in range(44):
			objid = random.randint(0,1e15)
			while(db.tools.find({"url_id":str(objid)}).count()!=0 or
			      db.generated_id.find({"url_id":str(objid)}).count()!=0):
				objid = random.randint(0,1e15)
			self.write("    <td><img src='"+options.home_url+"/g/"+str(objid)+"'></td>")
			db.generated_id.insert({"url_id":objid})
			if i%11 == 10:
				self.write("  </tr>\n  <tr>\n")
		self.write("  </tr>\n</table>")

class Generate65QRHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.set_header("Content-Type", "image/svg+xml")
		db = self.application.database
		#self.write("<table>\n  <tr>\n")
		urls=[]
		
		for i in range(66):
			objid = random.randint(0,1e15)
			while(db.tools.find({"url_id":str(objid)}).count()!=0 or
			      db.generated_id.find({"url_id":str(objid)}).count()!=0):
				objid = random.randint(0,1e15)
			#self.write("<img src='"+options.home_url+"/g/"+str(objid)+"'>")
			db.generated_id.insert({"url_id":objid})
			urls.append(options.home_url+"/g/"+str(objid))
			#if i%13 == 12:
			#	self.write("<br>\n")
		s = open("static/labels65.svg").read()
		print len(urls)
		self.write(s.format(*urls))

class Generate120QRHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.set_header("Content-Type", "image/svg+xml")
		db = self.application.database
		#self.write("<table>\n  <tr>\n")
		urls=[]
		
		for i in range(121):
			objid = random.randint(0,1e15)
			while(db.tools.find({"url_id":str(objid)}).count()!=0 or
			      db.generated_id.find({"url_id":str(objid)}).count()!=0):
				objid = random.randint(0,1e15)
			#self.write("<img src='"+options.home_url+"/g/"+str(objid)+"'>")
			db.generated_id.insert({"url_id":objid})
			urls.append(options.home_url+"/g/"+str(objid))
			#if i%13 == 12:
			#	self.write("<br>\n")
		s = open("static/labels120.svg").read()
		print len(urls)
		self.write(s.format(*urls))

class LoginHandler(BaseHandler):
	def get(self):
		self.write("You must be logged in to access this page.")
		
class AuthHandler(BaseHandler):
	def get(self):
		self.get("")
		
	def get(self, path):
		db=self.application.database
		userobj = db.users.find_one({"url": path })
		if userobj==None:
			raise tornado.web.HTTPError(500, "Unknown user/bad URL.")
		else:
			header(self)
			self.write("Welcome " + userobj['username'])
			self.set_secure_cookie("hfinv_user", tornado.escape.json_encode(userobj['username']))
			self.redirect("/")

class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
            autoescape=None,
            cookie_secret=options.cookie_secret,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            home_url=options.home_url,
            debug=True,
            login_url="/login",
        )

        handlers = [
            (r"/", MainHandler),
            (r"/o/(.*)", QRHandler),
            (r"/uploadpicture", UploadPicHandler),
            (r"/p/(.*)", PictureHandler),
            (r"/os", ObjectStatusHandler),
            (r"/auth/(.*)", AuthHandler),
            (r"/list", ListHandler),
            (r"/g/(.*)", GenerateQRHandler),
            (r"/g44", Generate44QRHandler),
            (r"/g65", Generate65QRHandler),
            (r"/g120", Generate120QRHandler),
            (r"/edit/(.*)", EditObjectHandler),
            (r"/login", LoginHandler),
            (r"/newobject", NewObjHandler)
        ]

        tornado.web.Application.__init__(self, handlers, **settings)

        self.con = Connection('localhost', 27017)
        self.database = self.con["hfinv"]
        self.gridfs = gridfs.GridFS(self.database)
        
    def check_expiry(self):
        db = self.database
        for l in db.documents.find({"expired":False}):
            exptime = datetime(*l["expiry"][:6])
            if datetime.now() > exptime:
                # l has expired
                db.documents.update({'_id': ObjectId(l['_id'])}, {"$set": {"expired" : True}})


def main():
	random.seed(None)
	tornado.options.parse_command_line()
	app = Application()
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

 
if __name__ == "__main__":
    main()
