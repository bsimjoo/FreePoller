import cherrypy
import lmdb
import configparser
import os
import chevron
import pickle

CONFIG_FILE = './config.ini'
POL_DB = b'pols'
USERS_DB = b'users'
DEBUG = True


class TemplatesCache:
    def __init__(self, templates_dir: str, cache: bool):
        self.cache = cache
        def get_path(x): return os.path.join(templates_dir, x)
        self.__templates = {
            'index': get_path('index.html'),
            'login': get_path('login.html'),
            'signup': get_path('signup.html'),
            'pol': get_path('pol.html'),
            'create': get_path('create.html')
        }
        if cache:
            for k, v in self.__templates:
                with open(v) as f:
                    self.__templates[k] = f.read()

    def get_template(self, template_key):
        if self.cache:
            return self.__templates[template_key]
        else:
            with open(self.__templates[template_key]) as template_file:
                template = template_file.read()
            return template


class Root:
    def __init__(self, env:lmdb.Environment, config: configparser.SectionProxy, templates:TemplatesCache):
        self.env = env
        self.config = config
        self.mountpoint = config.get('mount_point', '/')
        self.templates=templates
        self.usersdb = env.open_db(USERS_DB);
        self.pol = env.open_db(POL_DB);

    @cherrypy.expose
    def index(self, p=None):
        if p == None:
            return self.templates.get_template('index')
        else:
            #find pol
            with self.env.begin(self.pol) as txn:
                value = txn.get(p,default=None)
                if value:
                    data = pickle.loads(value)
                    return chevron.render(self.templates.get_template('pol'), data)
                else:
                    raise cherrypy.NotFound();


if __name__ == '__main__':
    cfg = configparser.ConfigParser()
    cfg.read_file(CONFIG_FILE)
    main_cfg = cfg['main']
    env = lmdb.open(main_cfg.get('lmdb_dir', '.db'), max_dbs=2)
    templates = TemplatesCache(main_cfg.get('templates_dir'), DEBUG)
    root = Root(env, cfg['root'])

    cherry_cfg = {
        "global":
        {
            "server.socket_host": main_cfg.get('host', '0.0.0.0'),
            "server.socket_port": main_cfg.getint('port', 8080),
            "server.socket_file": main_cfg.get('unix_socket'),
            "tools.sessions.on": True,
            "tools.staticdir.on": True,
            "tools.staticdir.dir": os.path.abspath("./webInterface/files/"),
            "tools.staticdir.root": "/",
            "environment": None if DEBUG else "production",
        }
    }

    cherrypy.quickstart(root, root.mountpoint, cherry_cfg)
