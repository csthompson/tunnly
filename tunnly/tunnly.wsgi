#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/tunnly/")

from tunnly import app as application
application.secret_key = 'xxxjjjtesttunnly1234567890'