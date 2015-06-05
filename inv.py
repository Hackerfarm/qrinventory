#!/usr/bin/env python
# -*- coding: utf-8

from datetime import datetime
from pymongo.connection import Connection
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

from markdown import markdown

from tornado.options import define, options

import config



class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("hfinv_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):
	def get(self):
		self.write("""
		<div type="title">Welcome, {0}</div>
		<div type="main_button" onmousedown="document.location = '/list'">View tools list</div>
		""".format(self.get_current_user()))

class ListHandler(BaseHandler):
	def get(self):
		self.write("""
		<div class="title">Welcome, {0}</div>
		<div class="list">Liste</div>
		""".format(self.get_current_user()))
		db = self.application.database
		for tool in db.tools.find():
			self.write("""<div id='tool_list_element'>
						<a href='/o/{link}'>
						<div><img width="150px" height="150px" src='/p/{img}'></div>
						<div id='tool_list_name'>{name}</div></a>
					</div>""".format(
						link=str(tool["url_id"]),
						img=str(tool["picture_id"]),
						name=tool["description_en"])
						)


class QRHandler(BaseHandler):
	def get(self, path):
		db = self.application.database
		results = db.tools.find({'url_id':path})
		if results.count()==0:
			self.write(u"""
			<form enctype="multipart/form-data" method="POST" action="/newobject" id="newobjform">
			{0}
			<input type="hidden" value="{1}" name="url_id"/>
			<div>
				<span>Description (Japanese)</span>
				<span><input type="text" name="description_jp"></input></span>
			</div>
			<div>
				<span>Description (English)</span>
				<span><input type="text" name="description_en"></input></span>
			</div>
			<div>
				<span>Owner</span>
				<span><input type="text" name="owner"></input></span>
			</div>
			<div>
				<span>Take a picture of the tool:</span>
				<span><input type="file" accept="image/*;capture=camera" name="pic"></span>
			</div>
			<div>
				<span>Current location of the tool</span>
				<span>
					<select name="location">
						<option>Hackefarm</option>
						<option>Maison Bleue</option>
						<option>SDF café</option>
						<option>Other</option>
					</select>
				</span>
				<span>Locate through GPS</span>
			</div>
			</form>
			<div onmousedown="document.getElementById('newobjform').submit()" type="main_button">Create new tool</div>
			
			""".format(self.xsrf_form_html(), path))
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
			<div type="main_button">
				<a href="/os?action=borrowing&object_id={object_id}">I am borrowing this object</a>
			</div>
			<div type="main_button">
				<a href="/os?action=returning&object_id={object_id}">I am returning this object</a>
			</div>
			<div type="main_button">
				<a href="/os?action=found&object_id={object_id}">I found this object</a>
			</div>
			""".format(description_en=tool.get("description_en",""),
			           description_jp=tool.get("description_jp",""),
			           location=tool.get("location",""),
			           owner=tool["owner"],
			           img_url=str(tool["picture_id"]),
			           object_id=path))

class ObjectStatusHandler(BaseHandler):
	def get(self):
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
			<select name="location">
				<option>Hackefarm</option>
				<option>Maison Bleue</option>
				<option>SDF café</option>
				<option>Other</option>
			</select>
			<input type="submit" value="Validate"/>
			{secure}
		</form>""".format(object_id = self.request.arguments.get("object_id",[""])[0],
		                  action = self.request.arguments.get("action",[""])[0],
		                  msg = msg,
		                  secure=self.xsrf_form_html()))
	def post(self):
		self.write(self.request.arguments.get("location", [""])[0])
		db = self.application.database
		db.actions.insert({
			"action":self.request.arguments.get("action",[""])[0],
			"user":self.get_current_user(),
			"location":self.request.arguments.get("location",[""])[0],
			"timestamp":datetime.now(),
			"object_id":self.request.arguments.get("object_id",[""])[0]})
		db.tools.update({"url_id":self.request.arguments.get("object_id",[""])[0]},
		                 {"$set": {"location": self.request.arguments.get("location",[""])[0]}})


class NewObjHandler(BaseHandler):
	def post(self):
		self.write("What do I get?<br>"+str(self.request.files['pic'][0]['filename']))
		img = Image.open(StringIO.StringIO(self.request.files['pic'][0]['body']))
		fs = self.application.gridfs
		db = self.application.database
		imgid = fs.put(StringIO.StringIO(self.request.files['pic'][0]['body']))

		newtool = {
		'owner': self.request.arguments.get("owner",[""])[0],
		'url_id': self.request.arguments.get("url_id")[0],
		'description_jp': self.request.arguments.get("description_jp", [""])[0],
		'description_en': self.request.arguments.get("description_en", [""])[0],
		'picture_id': imgid,
		'location': self.request.arguments.get("location", [""])[0]}
		db.tools.insert(newtool)

		self.write("<img src='/p/{0}'>".format(str(imgid)))

class UploadPicHandler(BaseHandler):
	def get(self):
		self.write("""
		<form enctype="multipart/form-data" method="POST" action="/uploadpicture">
			<input type="file" accept="image/*;capture=camera" name="pic">
			<input type="hidden" name="pouic" value="1">
			<input type="submit">
		</form> """)
		
	def post(self):
		self.write("What do I get?<br>"+str(self.request.files['pic'][0]['filename']))
		img = Image.open(StringIO.StringIO(self.request.files['pic'][0]['body']))
		img.save("./a", img.format)
		fs = self.application.gridfs
		db = self.application.database
		imgid = fs.put(StringIO.StringIO(self.request.files['pic'][0]['body']))
		self.write(str(imgid))
		#db.dev.insert({'imgid': imgid })


class PictureHandler(BaseHandler):
	def get(self):
		self.get("")
		
	def get(self, path):
		self.set_header("Content-Type", "image/gif")
		fs = self.application.gridfs
		db = self.application.database
		#imgid = db.dev.find_one({"imgid":{'$exists':True}})
		#self.write(fs.get(imgid["imgid"]).read())
		self.write(fs.get(ObjectId(path)).read())

class AuthHandler(BaseHandler):
	def get(self):
		self.get("")
		
	def get(self, path):
		db=self.application.database
		userobj = db.users.find_one({"url": path })
		if userobj==None:
			raise tornado.web.HTTPError(500, "Unknown user/bad URL.")
		else:
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
        )

        handlers = [
            (r"/", MainHandler),
            (r"/o/(.*)", QRHandler),
            (r"/uploadpicture", UploadPicHandler),
            (r"/p/(.*)", PictureHandler),
            (r"/os", ObjectStatusHandler),
            (r"/auth/(.*)", AuthHandler),
            (r"/list", ListHandler),
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
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

 
if __name__ == "__main__":
    main()
