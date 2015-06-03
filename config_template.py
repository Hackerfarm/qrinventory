#!/usr/bin/env python
# -*- coding: utf-8

# Fill, add some entropy and rename config.py


from tornado.options import define, options

define("port", default=8989, type=int)


define("home_url", help="The URL the website will be at", 
                   default="http://localhost:8989")  
 
define("cookie_secret", help="Some entropy for the cookie_secret", 
                   default="")
 
