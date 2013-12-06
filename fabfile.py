# vim: tabstop=4 shiftwidth=4 softtabstop=4

# This is a templated file generated from files/farmboy/fabfile.py,
# by commands such as `farmboy vagrant.init` will produce an output
# version in your local directory that you can then modify to your
# heart's content.

import os

from farmboy import aptcacher
from farmboy import aws
from farmboy import core
from farmboy import django
from farmboy import dns
from farmboy import files
from farmboy import gitlab
from farmboy import gunicorn
from farmboy import haproxy
from farmboy import jenkins
from farmboy import mysql
from farmboy import nginx
from farmboy import socks5
from farmboy import tomcat
from farmboy import util
from farmboy import vagrant


from fabric.api import env
from fabric.api import execute
from farmboy.fabric_ import task



# The Openstack utilities can launch your VMs for you using
# `farmboy openstack.build`. This setting tells them how many and which roles
# to use, it will cache their addresses by default into the farmboy.yaml
# file so that we can target them for the rest of our actions.
# POWER TIP: Use `farmboy openstack.refresh` to update the farmboy.yaml
#            file if you've manually changed your instances.
env.farmboy_os_instances = ['proxy', 'apt', 'db', 'web', 'web']

# We generally want to use a stock Ubuntu 13.04 cloud image, you'll need
# to figure out the ID of one (or upload it using the dashboard).
# POWER TIP: Or you can use our handy picker! `farmboy openstack.images`
env.farmboy_os_image_id = util.load('farmboy_os_image_id', 'farmboy.yaml')

# We usually use the `m1.small` flavor, if this isn't configured already
# the `farmboy openstack.build` command will prompt you with choices.
# POWER TIP: You can use our handy picker! `farmboy openstack.flavors`
env.farmboy_os_flavor_id = util.load('farmboy_os_flavor_id', 'farmboy.yaml')

# We generally want to use a stock Ubuntu 13.04 cloud image, you'll need
# to figure out the ID of one (or upload it using the dashboard).
# POWER TIP: Or you can use our handy picker!
env.farmboy_os_image_id = util.load('farmboy_os_image_id', 'farmboy.yaml')

# If you are using an Openstack cloud that is using Neutron, you need to
# to do some additional network config.
# POWER TIP: Piccckkkeerrr: `farmboy openstack.networks`
env.farmboy_os_use_neutron = False
if env.farmboy_os_use_neutron:
  env.farmboy_os_network_id = util.load('farmboy_os_network_id',
                                        'farmboy.yaml')
  env.farmboy_os_network_name = util.load('farmboy_os_network_name',
                                          'farmboy.yaml')

# If you want to use floating ips by default, you can set this to True
# POWER TIP: This just calls `farmboy openstack.associate_floating_ips` after
#            running the build task, you can call that yourself, too.
env.farmboy_os_use_floating_ips = False

# These are the various Openstack-related configuration options and their
# default values. They should be pretty self explanatory for people who've
# used OpenStack.

# env.farmboy_os_username = os.environ.get('OS_USERNAME', '')
# env.farmboy_os_password = os.environ.get('OS_PASSWORD', '')
# env.farmboy_os_tenant_name = os.environ.get('OS_TENANT_NAME', '')
# env.farmboy_os_auth_url = os.environ.get('OS_AUTH_URL', '')

# env.farmboy_os_image_user = 'ubuntu'
# env.farmboy_os_reservation_id = 'farmboy'
# env.farmboy_os_security_group = 'farmboy'
# env.farmboy_os_keypair = 'farmboy'
# env.farmboy_os_keyfile = 'farmboy.key'
# env.farmboy_os_keyfile_public = 'farmboy.key.pub'


# We're using `python-novaclient` for the built-in OpenStack tools, so if you
# use those you should define the common OpenStack environment variables in
# your shell:
#
#   OS_USERNAME
#   OS_PASSWORD
#   OS_TENANT_NAME
#   OS_AUTH_URL



# Private key that we'll use to connect to the machines
env.key_filename = 'farmboy.key'

# Define which servers go with which roles.
# POWER TIP: These can defined as callables as well if you want to load
#            the servers in some more dynamic way.
# POWER TIP: You might also want to separate these out into a yaml file
#            and do `env.roledefs = yaml.load(open('farmboy.yaml'))`
#            or use the helper `env.roledefs = util.load_roledefs()`
env.roledefs.update(util.load_roledefs('farmboy.yaml'))

# Since we're be using apt caching, point out where that proxy will live.
# POWER TIP: If you're already using such a proxy, you can just point this
#            at that server and skip the `execute(aptcacher.deploy)` step.
if env.roledefs.get('apt'):
    apt = env.roledefs['apt'][0]
    env.farmboy_apt_proxy = 'http://%s:3142' % util.host(apt)

# Let's load our MySQL password from our local yaml file, too.
# If there isn't one in there, we'll auto-generate one during the
# `mysql.deploy` step.
env.farmboy_mysql_password = util.load('farmboy_mysql_password')

# Where our django app lives (this directory will be pushed to web servers).
# This is expected to be the directory that contains the manage.py file for
# a default django setup.
# POWER TIP: We expect this to be in the current directory by default
#            but a full path works here, too.
# POWER TIP: You can set the path directly as we do below in the execute
#            call, but if none is set it will default to using the this
#            env variable.
env.farmboy_django_app = 'demo'

# Where to find the template files to use when configuring services.
# POWER TIP: We'll fall back to the defaults shipped with farmboy for
#            any files not found in this location.
# POWER TIP: TODO(termie) Use `farmboy files $some_module` to get the
#            list and locations of files used for a given module.
env.farmboy_files = './files'

import fabtools.require
from fabric.contrib import project
from fabric.api import roles
from fabric.api import run
from fabric.api import sudo
from fabric.context_managers import cd

@task
@roles('db')
def alembic_upgrade():
    """Copy our alembic versions to the mysql box and execute them."""
    local_path = './alembic'
    password = util.load('farmboy_mysql_password_refstack')

    # Make sure alembic is installed
    fabtools.require.deb.packages(['build-essential',
                                   'python-dev',
                                   'libmysqlclient-dev'])
    fabtools.require.python.package('alembic', use_sudo=True)
    fabtools.require.python.package('mysql-python', use_sudo=True)

    # Copy our alembic files over
    project.rsync_project(local_dir=local_path,
                          remote_dir='.',
                          ssh_opts=('-o UserKnownHostsFile=/dev/null'
                                    ' -o StrictHostKeyChecking=no'))

    fabtools.require.files.template_file(
        template_source = 'alembic.ini',
        path = 'alembic.ini',
        context  = {'password': password},
        owner    = 'root',
        group    = 'root',
        mode     = '600',
        use_sudo = True)

    sudo('alembic upgrade head')


@task
@roles('web')
def refstack_deps():
    fabtools.require.python.package('pip', use_sudo=True)
    fabtools.require.deb.packages(['build-essential',
                                   'python-dev',
                                   'libmysqlclient-dev'])
    fabtools.require.python.package('mysql-python', use_sudo=True)

    project.rsync_project(remote_dir='.',
                          exclude=['logs', 'openid', 'uploads'],
                          ssh_opts=('-o UserKnownHostsFile=/dev/null'
                                    ' -o StrictHostKeyChecking=no'))
    with cd('refstack'):
        sudo('pip install -r requirements.txt')


@task
@roles('web')
def refstack_deploy():
    password = util.load('farmboy_mysql_password_refstack')
    remote_path = run('echo $HOME/refstack')

    project.rsync_project(remote_dir='.',
                          exclude=['logs', 'openid', 'uploads'],
                          ssh_opts=('-o UserKnownHostsFile=/dev/null'
                                    ' -o StrictHostKeyChecking=no'))

    fabtools.require.files.directory('/tmp/instance',
                                     owner='www-data',
                                     group='www-data',
                                     mode='755',
                                     use_sudo=True)

    fabtools.require.files.template_file(
        template_source = 'refstack.cfg',
        path = '/tmp/instance/refstack.cfg',
        context = {'password': password},
        owner = 'www-data',
        group = 'www-data',
        mode = '600',
        use_sudo = True)

    fabtools.require.files.template_file(
        template_source = util.files('gunicorn/flask'),
        path     = '/etc/gunicorn.d/refstack',
        context  = {'working_dir': remote_path,
                    'wsgi_app': 'refstack.web:app',
                    'instance_folder_path': '/tmp/instance'},
        owner    = 'root',
        group    = 'root',
        mode     = '644',
        use_sudo = True)

    gunicorn.restart()


@task(default=True)
def demo():
    """Example deployment of an haproxy+nginx+gunicorn+django."""
    execute(dns.hosts)
    if env.roledefs.get('apt'):
        execute(aptcacher.deploy)
        execute(aptcacher.set_proxy)
    execute(core.install_user)
    execute(mysql.deploy)
    execute(mysql.create_user, name='refstack', user_host='localhost')
    execute(mysql.create_user, name='refstack', user_host='%')
    execute(mysql.create_database,
            name='refstack',
            owner='refstack',
            owner_host='%')
    execute(alembic_upgrade)
    execute(haproxy.deploy)
    execute(nginx.deploy)
    execute(gunicorn.deploy)
    execute(refstack_deps)
    execute(refstack_deploy)
    #execute(django.deploy, path=env.farmboy_django_app)

    print ('Alright! Check out your site at: http://%s'
            % util.host(env.roledefs['proxy'][0]))
