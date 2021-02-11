import cherrypy
import lmdb
im

class Root:
    def __init__(self, env, db, config):
