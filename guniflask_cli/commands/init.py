import json
import os
import re
from os.path import exists, join, abspath, isdir, basename, dirname, relpath, isfile
from shutil import ignore_patterns

import click
import inquirer
from inquirer.errors import ValidationError
from inquirer.themes import GreenPassion
from jinja2 import Environment

from guniflask_cli import __version__
from guniflask_cli.config import _template_folder
from guniflask_cli.errors import AbortedError, TemplateError
from guniflask_cli.utils import string_lowercase_underscore


@click.group()
def cli_init():
    pass


@cli_init.command('init')
@click.option('-d', '--root-dir', metavar='DIR', help='Application root directory.')
@click.option('-f', '--force', default=False, is_flag=True, help='Force generating an application.')
def main(root_dir, force):
    """
    Initialize a project.
    """
    Init().run(root_dir, force)


class Init:
    def run(self, root_dir, force):
        project_dir = abspath(root_dir or '')
        self.print_welcome(project_dir)
        try:
            init_json_file = join(project_dir, '.guniflask-init.json')
            old_settings = {}
            try:
                with open(init_json_file, 'r', encoding='utf-8') as f:
                    old_settings = json.load(f)
                if force:
                    raise FileNotFoundError
                settings = old_settings
                self.print_regenerate_project()
            except (FileNotFoundError, json.JSONDecodeError):
                settings = self.get_settings_by_steps(project_dir, old_settings=old_settings)
                with open(init_json_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, sort_keys=True)
            self.copy_files(project_dir, settings)
        except (KeyboardInterrupt, AbortedError):
            print(flush=True)
            self.print_aborted_error()
            self.exitcode = 1

    def get_settings_by_steps(self, project_dir: str, old_settings: dict = None):
        default_base_name = old_settings.get(
            'project_name',
            string_lowercase_underscore(basename(project_dir)),
        )
        default_authentication_type = old_settings.get('authentication_type')
        default_port = old_settings.get('port', 8000)
        questions = [
            inquirer.Text(
                'project_name',
                message='What is the base name of your application?',
                default=default_base_name,
                validate=self.validate_app_name,
            ),
            inquirer.Text(
                'port',
                message='Would you like to run your application on which port?',
                default=default_port,
                validate=self.validate_port,
            ),
            inquirer.List(
                'authentication_type',
                message='Which type of authentication would you like to use?',
                choices=[
                    ('No authentication', None),
                    ('JWT authentication', 'jwt'),
                ],
                default=default_authentication_type,
            ),
        ]
        answers = inquirer.prompt(questions, theme=GreenPassion(), raise_keyboard_interrupt=True)
        settings = {
            'cli_version': __version__,
        }
        settings.update(answers)
        if settings.get('authentication_type') == 'jwt':
            from guniflask.security import JwtHelper
            settings['jwt_secret'] = JwtHelper.generate_jwt_secret()
        return settings

    @staticmethod
    def validate_app_name(answers, current):
        if current and re.match(r'^[0-9a-zA-Z_]+$', current) and not str.isdigit(current[0]):
            return True
        raise ValidationError(
            '',
            reason='Please input a base name' if not current else f'"{current}" is not a valid base name'
        )

    @staticmethod
    def validate_port(answers, current):
        if current and re.match(r'^[0-9]+$', current):
            return True
        raise ValidationError(
            '',
            reason='Please input a port' if not current else f'"{current}" is not a valid port'
        )

    def copy_files(self, project_dir, settings):
        settings = dict(settings)
        settings['project_dir'] = project_dir
        settings['guniflask_min_version'] = __version__
        version_info = __version__.split('.')
        if version_info[0] == '0':
            settings['guniflask_max_version'] = f'{version_info[0]}.{int(version_info[1]) + 1}'
        else:
            settings['guniflask_max_version'] = f'{int(version_info[0]) + 1}.0'
        self.infer_project_version(project_dir, settings)

        self.print_copying_files()
        self.force = False
        self.ignore_files = self.resolve_ignore_files(settings)
        self.filename_mapping = self.make_filename_mapping(settings)

        self.copytree(join(_template_folder, 'project'), project_dir, settings)
        print(flush=True)
        self.print_success()

    def infer_project_version(self, project_dir, settings):
        project_name = settings['project_name']
        p = join(project_dir, project_name, '__init__.py')
        if isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                s = re.search(r"__version__ = '([^']+)'", f.read())
        else:
            s = None
        if s:
            version = s.group(1)
        else:
            version = '0.0.0'
        settings['project_version'] = version

    def resolve_ignore_files(self, settings):
        ignore_files = set()
        project_name = settings['project_name']
        if settings['authentication_type'] != 'jwt':
            ignore_files.add(f'{project_name}/config/jwt_config.py')
        return ignore_files

    def make_filename_mapping(self, settings):
        m = {
            '_project_name': settings['project_name'],
            '_project_name.py': f'{settings["project_name"]}.py'
        }
        return m

    def copytree(self, src, dst, settings):
        names = os.listdir(src)
        ignored_names = ignore_patterns('*.pyc')(src, names)
        for name in names:
            if name in ignored_names:
                continue
            src_path = join(src, name)
            dst_name, is_template = self.resolve_filename(name)
            dst_path = join(dst, dst_name)
            dst_rel_path = relpath(dst_path, settings['project_dir'])

            if isdir(src_path):
                self.copytree(src_path, dst_path, settings)
            else:
                content = self.read_file(src_path)
                if is_template:
                    content = self.render_string(content, **settings)

                if dst_rel_path in self.ignore_files:
                    continue
                if exists(dst_path):
                    raw = self.read_file(dst_path)
                    if content == raw:
                        self.print_copying_file('identical', dst_rel_path)
                    else:
                        if self.force:
                            self.print_copying_file('force', dst_rel_path)
                            self.write_file(dst_path, content)
                        else:
                            self.print_copying_file('conflict', dst_rel_path)
                            user_input = inquirer.text(
                                message=f'Overwrite {dst_rel_path}? (Y/n/a/x)',
                                validate=self.validate_conflict_command,
                            )
                            if not user_input or user_input == 'y' or user_input == 'a':
                                self.print_copying_file('force', dst_rel_path)
                                self.write_file(dst_path, content)
                                if user_input == 'a':
                                    self.force = True
                            elif user_input == 'n':
                                self.print_copying_file('skip', dst_rel_path)
                            elif user_input == 'x':
                                raise AbortedError
                else:
                    self.print_copying_file('create', dst_rel_path)
                    self.write_file(dst_path, content)

    @staticmethod
    def read_file(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def write_file(path, raw):
        d = dirname(path)
        if not exists(d):
            os.makedirs(d)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(raw)

    def resolve_filename(self, name):
        if name.endswith('.jinja2'):
            is_template = True
            name = name.rsplit('.', maxsplit=1)[0]
        else:
            is_template = False
        if name in self.filename_mapping:
            name = self.filename_mapping[name]
        return name, is_template

    @staticmethod
    def render_string(raw, **kwargs):
        env = jinja2_env()
        return env.from_string(raw).render(**kwargs)

    @staticmethod
    def print_welcome(project_dir):
        print(f'\033[37mWelcome to guniflask generator\033[0m \033[33mv{__version__}\033[0m', flush=True)
        print(f'\033[37mApplication files will be created in folder:\033[0m \033[33m{project_dir}\033[0m', flush=True)

    @staticmethod
    def print_regenerate_project():
        print('\033[32mThis is an existing project, using the configuration from .guniflask-init.json '
              'to regenerate the project...\033[0m', flush=True)

    @staticmethod
    def print_success():
        print('\033[32mApplication is created successfully.\033[0m', flush=True)

    @staticmethod
    def print_aborted_error():
        print('\033[33mProcess is aborted by user.\033[0m', flush=True)

    @staticmethod
    def print_copying_files():
        print('Copying files:', flush=True)

    @staticmethod
    def print_copying_file(t, path):
        color = 0
        if t == 'identical':
            color = 36
        elif t == 'conflict':
            color = 31
        elif t == 'create':
            color = 32
        elif t == 'force' or t == 'skip':
            color = 33
        print(f'\033[{color}m{t:>9}\033[0m {path}', flush=True)

    @staticmethod
    def validate_conflict_command(answers, current):
        if current and current not in 'ynax':
            raise ValidationError(
                '',
                reason=f'"{current}" is not a valid command'
            )
        return True


def jinja2_env():
    def _raise_helper(message):
        if message:
            raise TemplateError(message)
        raise TemplateError

    def _assert_helper(logical, message=None):
        if not logical:
            _raise_helper(message)
        return ''

    env = Environment(keep_trailing_newline=True)
    env.globals['raise'] = _raise_helper
    env.globals['assert'] = _assert_helper
    return env
