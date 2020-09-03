# coding=utf-8

import os
import sys
from os.path import join, isfile, isdir
import re
import json

from dotenv import load_dotenv


def set_default_env():
    home_dir = os.environ.get('GUNIFLASK_HOME')
    if not home_dir:
        home_dir = os.getcwd()
        os.environ['GUNIFLASK_HOME'] = home_dir
    if home_dir not in sys.path:
        sys.path.append(home_dir)
    if not os.environ.get('GUNIFLASK_CONF_DIR'):
        os.environ['GUNIFLASK_CONF_DIR'] = join(home_dir, 'conf')
    if not os.environ.get('GUNIFLASK_LOG_DIR'):
        os.environ['GUNIFLASK_LOG_DIR'] = join(home_dir, '.log')
    if not os.environ.get('GUNIFLASK_PID_DIR'):
        os.environ['GUNIFLASK_PID_DIR'] = join(home_dir, '.pid')


def load_env(fname):
    if fname is None or not isfile(fname):
        raise FileNotFoundError("Cannot find env file '{}'".format(fname))
    load_dotenv(fname)


def load_profile_env(conf_dir, profiles: str = None):
    base_file = join(conf_dir, 'app.env')
    if isfile(base_file):
        load_env(base_file)
    if profiles:
        profiles = profiles.split(',')
        for profile in reversed(profiles):
            if profile:
                p_file = join(conf_dir, f'app_{profile}.env')
                if isfile(p_file):
                    load_env(p_file)


def load_app_env():
    conf_dir = os.environ.get('GUNIFLASK_CONF_DIR')
    active_profiles = os.environ.get('GUNIFLASK_ACTIVE_PROFILES')
    load_profile_env(conf_dir, active_profiles)


project_name_regex = re.compile(r'[a-zA-Z\-]+')


def infer_project_name(home_dir):
    init_file = join(home_dir, '.guniflask-init.json')
    if isfile(init_file):
        try:
            with open(init_file, 'r') as f:
                data = json.load(f)
            project_name = data.get('project_name')
            if project_name and isdir(join(home_dir, project_name)):
                return project_name
        except Exception:
            pass
    candidates = []
    for d in os.listdir(home_dir):
        if project_name_regex.fullmatch(d) and isfile(join(home_dir, d, '__init__.py')) \
                and isfile(join(home_dir, d, 'app.py')):
            candidates.append(d)
    if len(candidates) == 0:
        return None
    if len(candidates) > 1:
        raise RuntimeError('Cannot infer the project name, candidates: {}'.format(candidates))
    return candidates[0]


def get_project_name_from_env():
    if not os.environ.get('GUNIFLASK_PROJECT_NAME'):
        project_name = infer_project_name(os.environ.get('GUNIFLASK_HOME'))
        if project_name:
            os.environ['GUNIFLASK_PROJECT_NAME'] = project_name
    return os.environ.get('GUNIFLASK_PROJECT_NAME')
