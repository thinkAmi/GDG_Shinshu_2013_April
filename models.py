# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

class Phone(ndb.Model):
    talk = ndb.StringProperty()