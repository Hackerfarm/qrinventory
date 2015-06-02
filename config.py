#!/usr/bin/env python
# -*- coding: utf-8

from tornado.options import define, options

define("port", default=8989, type=int)


define("home_url", help="The URL the website will be at", 
                   default="http://localhost:8989")  
 
define("cookie_secret", help="", 
                   default="")
 
