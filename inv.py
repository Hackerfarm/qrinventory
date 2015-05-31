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
        user_json = self.get_secure_cookie("noy_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):
	def get(self):
		self.write("""
		<div type="main_button">View tools list</div>
		""")


class QRHandler(BaseHandler):
	def get(self, path):
		db = self.application.database
		results = db.tools.find({'url_id':path})
		if results.count()==0:
			self.write("""
			<div>
				<span>Description (Japanese)</span>
				<span><input type="text" name="description-jp"></input></span>
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
				
			<div type="main_button">Create new tool</div>
			""")
		else:
			self.write("""
			<div type="description">Handsaw</div>
			<img src="/p/{0}>
			<div type="main_button">I am borrowing this object</div>
			<div type="main_button">I am returning this object</div>
			<div type="main_button">I found this object</div>
			""").format(path)

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


class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
            autoescape=None,
            cookie_secret=options.cookie_secret,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            #xsrf_cookies=True,
            home_url=options.home_url,
            debug=True,
        )

        handlers = [
            (r"/", MainHandler),
            (r"/o/(.*)", QRHandler),
            (r"/uploadpicture", UploadPicHandler),
            (r"/p/(.*)", PictureHandler)
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
