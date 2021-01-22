import logging
import os
from functools import partial
from os.path import join, dirname, exists

from gunicorn.app.base import Application
from gunicorn.config import KNOWN_SETTINGS

from .utils import walk_files, redirect_app_logger, redirect_logger


class GunicornApplication(Application):

    def __init__(self, **options):
        self.options: dict = options
        super().__init__()

    def set_option(self, key, value):
        if key in self.cfg.settings:
            self.cfg.set(key, value)

    def load_config(self):
        from guniflask.config import set_app_default_env
        set_app_default_env()
        self.options = self._make_options(self.options)
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)
        self._set_default_env()

    def load(self):
        from guniflask.app import create_app
        from guniflask.config import app_name_from_env

        gunicorn_logger = logging.getLogger('gunicorn.error')
        app_name = app_name_from_env()
        redirect_logger('guniflask', gunicorn_logger)
        redirect_logger(app_name, gunicorn_logger)

        app = create_app()
        redirect_app_logger(app, gunicorn_logger)
        return app

    def _make_options(self, opt: dict):
        from guniflask.config import app_name_from_env
        home_dir = os.environ.get('GUNIFLASK_HOME')
        pid_dir = join(home_dir, '.pid')
        log_dir = join(home_dir, '.log')
        app_name = app_name_from_env()
        options = {
            'daemon': True,
            'workers': os.cpu_count(),
            'worker_class': 'gevent',
            'accesslog': join(log_dir, f'{app_name}.access.log'),
            'errorlog': join(log_dir, f'{app_name}.error.log'),
            'proc_name': app_name
        }
        profile_options = self._make_profile_options(os.environ.get('GUNIFLASK_ACTIVE_PROFILES'))
        options.update(profile_options)
        # if debug
        if os.environ.get('GUNIFLASK_DEBUG'):
            self._update_debug_options(options)
        options.update(opt)
        # pid file
        if 'pidfile' not in options and options.get('daemon'):
            options['pidfile'] = join(pid_dir, f'{app_name}.pid')
        self._makedirs(options)
        # hook wrapper
        HookWrapper.wrap(options)
        return options

    def _make_profile_options(self, active_profiles):
        from guniflask.config import load_profile_config
        conf_dir = os.environ['GUNIFLASK_CONF_DIR']
        gc = load_profile_config(conf_dir, 'gunicorn', profiles=active_profiles)
        settings = {}
        snames = set([i.name for i in KNOWN_SETTINGS])
        for name in gc:
            if name in snames:
                settings[name] = gc[name]
        return settings

    @staticmethod
    def _update_debug_options(options: dict):
        conf_dir = os.environ['GUNIFLASK_CONF_DIR']
        opt = {
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'debug',
            'reload': True,
            'reload_extra_files': walk_files(conf_dir),
            'workers': 1,
            'daemon': False
        }
        if 'reload_extra_files' in options:
            opt['reload_extra_files'].extend(options['reload_extra_files'])
        options.update(opt)

    @staticmethod
    def _makedirs(opts):
        for c in ['pidfile', 'accesslog', 'errorlog']:
            p = opts.get(c)
            if p:
                d = dirname(p)
                if d and not exists(d):
                    os.makedirs(d)

    def _set_default_env(self):
        bind = self.options.get('bind', '127.0.0.1:8000')
        if not isinstance(bind, str):
            raise ValueError(f'Invalid bind: {bind}')

        port = 80
        s = bind.split(':')
        host = s[0]
        if len(s) > 1:
            port = int(s[1])

        os.environ['GUNIFLASK_HOST'] = host
        os.environ['GUNIFLASK_PORT'] = str(port)


class HookWrapper:
    HOOKS = ['on_starting', 'on_reload', 'on_exit']

    def __init__(self, user_hooks, sys_hooks):
        self.user_hooks = user_hooks
        self.sys_hooks = sys_hooks

    @classmethod
    def wrap(cls, config, **kwargs):
        user_hooks = {}
        for h in cls.HOOKS:
            if h in config:
                user_hooks[h] = config[h]
        w = cls(user_hooks, kwargs)
        for h in cls.HOOKS:
            if h in w.user_hooks or h in w.sys_hooks:
                config[h] = partial(w.on_event, key=h)
        return w

    def on_event(self, server, key=None):
        if key in self.user_hooks:
            self.user_hooks[key](server)
        if key in self.sys_hooks:
            self.sys_hooks[key](server)
