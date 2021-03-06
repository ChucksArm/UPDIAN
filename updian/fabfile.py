# fabfile.py - fabric deployment script
#
#  Copyright (c) 2007-2013 RobHost GmbH <support@robhost.de>
#
#  Author: Dirk Dankhoff <dd@robhost.de>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA
'''Fabfile containing all operations needed to deploy Updian locally.'''
from __future__ import print_function

import os
import sys

import fabric.colors
from fabric.api import task, local, cd
from fabric.contrib.console import confirm

venv_path = os.path.join(os.getcwd(), 'updian-venv')

def warning(text, prefix='Warning:'):
    print(fabric.colors.yellow(prefix + ' ', bold=True) + text)

def make_virtual_environment():
    python_bin = sys.executable
    if sys.version_info[0] == 2 and sys.version_info[1] > 6:
        if os.path.exists('/usr/bin/python2.6'):
            python_bin = '/usr/bin/python2.6'
        else:
            warning('You are running a Python version greater than 2.6 and '
                    'there was no python2.6 executable found in /usr/bin. '
                    'Performance could suffer as a result of this.\n'
                    '[see: https://github.com/paramiko/paramiko/issues/191]')

    local('virtualenv --python=%s --no-site-packages %s' %
          (python_bin, venv_path))

def activate_virtual_environment():
    activate_this = os.path.join(venv_path, 'bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

def install_updian():
    try:
        import updian
    except ImportError:
        local('pip install updian')

def make_runtime_directories():
    mode = 0750
    os.mkdir('log/', mode)
    os.mkdir('data/', mode)
    os.mkdir('todo/', mode)

def link_frontend_data():
    import updian
    base_dir = os.path.join(os.path.dirname(updian.__file__), 'frontend')
    cur_dir = os.getcwd()

    for d in ['static']:
        src_dir = os.path.join(base_dir, d)
        dst_dir = os.path.join(cur_dir, d)
        os.symlink(src_dir, dst_dir)

def initialize_config():
    print('Creating user for basic authentication...')
    local('updiancmd setpw')
    print('Initializing configuration...')
    local('updiancmd init_cfg')

    if not os.path.exists('updian.wsgi'):
        with open('updian.wsgi', 'w') as wsgi_file:
            print('from updian.frontend import app as application',
                  file=wsgi_file)

def completion_message():
    print()
    print('Updian is now installed.')
    print('You should now edit the file `config.ini` to your liking.')
    print('Afterwards you can use `updiancmd runserver [IP]` to start the '
          'builtin Flask web server or configure your webserver to serve the '
          'wsgi application from the updian.wsgi in this directory.')
    print()
    warning('Only use the builtin web server if you serve Updian using a '
            'secure local network interface.', prefix='Note:')

@task
def make_dist():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    with cd(os.path.abspath(base_dir)):
        local('python setup.py sdist')

@task(default=True)
def deploy():
    if not confirm('Installing Updian to the current directory (%s). '
                   'Continue?' % os.getcwd()):
        return

    if 'VIRTUAL_ENV' not in os.environ:
        make_virtual_environment()
        activate_virtual_environment()
    else:
        warning('You are already inside a virtual environment (%s). '
                'Updian will be installed inside it.' %
                os.environ['VIRTUAL_ENV'])
        install_to_current_venv = confirm('Is this correct?')
        if not install_to_current_venv:
            create_new_venv = confirm('Should we create a new virtual '
                                      'environment?')
            if create_new_venv:
                make_virtual_environment()
                activate_virtual_environment()
            else:
                print('Cannot continue. Aborting.')
                sys.exit(1)

    install_updian()
    make_runtime_directories()
    link_frontend_data()
    initialize_config()
    completion_message()
