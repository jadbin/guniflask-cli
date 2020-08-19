# coding=utf-8

import os
from os.path import join, dirname, exists
from functools import partial
import logging
import getpass

from gunicorn.config import KNOWN_SETTINGS
from gunicorn.app.base import Application

from .config import load_profile_config, load_app_settings
from .utils import walk_files, redirect_app_logger, redirect_logger
from .env import get_project_name_from_env

__all__ = ['GunicornApplication']


class GunicornApplication(Application):

    def __init__(self, **options):
        self.options: dict = options
        super().__init__()

    def set_option(self, key, value):
        if key in self.cfg.settings:
            self.cfg.set(key, value)

    def load_config(self):
        self.options = self._make_options(self.options)
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        from guniflask.app import create_app

        self._set_default_env()
        app_name = get_project_name_from_env()
        app_settings = load_app_settings(app_name)

        gunicorn_logger = logging.getLogger('gunicorn.error')
        redirect_logger('guniflask', gunicorn_logger)
        redirect_logger(app_name, gunicorn_logger)
        app = create_app(app_name, settings=app_settings)
        redirect_app_logger(app, gunicorn_logger)
        return app

    def _make_options(self, opt: dict):
        pid_dir = os.environ['GUNIFLASK_PID_DIR']
        log_dir = os.environ['GUNIFLASK_LOG_DIR']
        project_name = get_project_name_from_env()
        username = getpass.getuser()
        options = {
            'daemon': True,
            'workers': os.cpu_count(),
            'worker_class': 'gevent',
            'accesslog': join(log_dir, '{}-{}.access.log'.format(project_name, username)),
            'errorlog': join(log_dir, '{}-{}.error.log'.format(project_name, username)),
            'proc_name': project_name
        }
        options.update(self._make_profile_options(os.environ.get('GUNIFLASK_ACTIVE_PROFILES')))
        # if debug
        if os.environ.get('GUNIFLASK_DEBUG'):
            options.update(self._make_debug_options())
        options.update(opt)
        # pid file
        if 'pidfile' not in options and options.get('daemon'):
            options['pidfile'] = join(pid_dir, '{}-{}.pid'.format(project_name, username))
        self._makedirs(options)
        # hook wrapper
        HookWrapper.wrap(options)
        return options

    def _make_profile_options(self, active_profiles):
        conf_dir = os.environ['GUNIFLASK_CONF_DIR']
        gc = load_profile_config(conf_dir, 'gunicorn', profiles=active_profiles)
        settings = {}
        snames = set([i.name for i in KNOWN_SETTINGS])
        for name in gc:
            if name in snames:
                settings[name] = gc[name]
        return settings

    @staticmethod
    def _make_debug_options():
        conf_dir = os.environ['GUNIFLASK_CONF_DIR']
        return {
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'debug',
            'disable_redirect_access_to_syslog': True,
            'reload': True,
            'reload_extra_files': walk_files(conf_dir),
            'workers': 1,
            'daemon': False
        }

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
            raise ValueError('Invalid bind: {}'.format(bind))

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
