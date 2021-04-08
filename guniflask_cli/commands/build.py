import os
import shutil
from importlib import import_module
from os.path import join, basename, exists, isdir, dirname

import click

from ..utils import ignore_by_patterns


@click.group()
def cli_build():
    pass


@cli_build.command('build')
def main():
    """
    Build application.
    """
    Build().run()


class Build:
    def run(self):
        from guniflask.config import app_name_from_env, set_app_default_env

        set_app_default_env()
        app_name = app_name_from_env()
        app_module = import_module(app_name)
        app_version = getattr(app_module, '__version__', None)
        home_dir = os.environ.get('GUNIFLASK_HOME')
        app_dir_name = basename(home_dir)
        dist_dir = join(home_dir, 'dist', app_dir_name if app_version is None else f'{app_dir_name}-{app_version}')
        includes = self.get_default_includes(app_name)

        self.copy_files(dist_dir, home_dir, includes)
        self.build(dist_dir, app_name)

    def copy_files(self, dist_dir, home_dir, includes):
        if exists(dist_dir):
            shutil.rmtree(dist_dir)
        os.makedirs(dist_dir)

        self.copy_ignore = ['*.pyc', '__pycache__']
        for d in includes:
            self.copy_tree(join(home_dir, d), join(dist_dir, d))

    def copy_tree(self, src, dst):
        if not isdir(src):
            d = dirname(dst)
            if not exists(d):
                os.makedirs(d)
            shutil.copy(src, dst)
            return

        names = os.listdir(src)
        ignored_names = ignore_by_patterns(src, names, self.copy_ignore)
        for name in names:
            if name in ignored_names:
                continue
            src_path = join(src, name)
            dst_path = join(dst, name)
            self.copy_tree(src_path, dst_path)

    def get_default_includes(self, app_name):
        includes = [
            app_name,
            'bin',
            'conf',
            'requirements',
            'tests',
            '.dockerignore',
            'docker-compose.yml',
            'Dockerfile',
        ]
        return includes

    def build(self, dist_dir, app_name):
        self.build_ignore = ['bin/*', 'conf/*', join(app_name, 'app.py')]
        self.build_dist = dist_dir

        for name in os.listdir(dist_dir):
            self.build_tree(name)

        shutil.rmtree(join(dist_dir, 'build'))

    def build_tree(self, src):
        if not isdir(src):
            return

        names = os.listdir(join(self.build_dist, src))
        ignored_names = ignore_by_patterns(src, names, self.build_ignore)

        py_to_build = []
        for name in names:
            if name in ignored_names:
                continue
            if name.endswith('.py'):
                py_to_build.append(name)

            src_path = join(src, name)
            self.build_tree(src_path)
        self.build_py_file(src, py_to_build)

    def build_py_file(self, src, names):
        if not names:
            return

        module_files = [join(src, i) for i in names]
        script = build_py_script.replace(
            '#home#',
            repr(join(self.build_dist)),
        ).replace(
            '#modules#',
            repr(module_files),
        )
        setup_file = join(self.build_dist, src, '__build_setup__.py')
        with open(setup_file, 'w') as f:
            f.write(script)
        os.system(f'cd "{self.build_dist}" && python "{setup_file}" build_ext --inplace')

        os.remove(setup_file)
        for name in names:
            c_file = join(self.build_dist, src, name.split('.')[0] + '.c')
            os.remove(c_file)
            py_file = join(self.build_dist, src, name)
            os.remove(py_file)


build_py_script = """import sys
from distutils.core import setup

from Cython.Build import cythonize

sys.path.insert(0, #home#)

setup(
    name='cython_build',
    ext_modules=cythonize(#modules#),
)
"""
