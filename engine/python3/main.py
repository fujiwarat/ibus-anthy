# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2025 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2016 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import os
from os import path
import sys
import getopt
import locale
import xml.dom.minidom

from gi import require_version as gi_require_version
gi_require_version('GLib', '2.0')
gi_require_version('IBus', '1.0')

from gi.repository import GLib

# set_prgname before importing factory to show the name in warning
# messages when import modules are failed. E.g. Gtk.
GLib.set_prgname('ibus-engine-anthy')

from gi.repository import IBus

import _config as config


def ibus_check_version(v):
    major = IBus.MAJOR_VERSION
    minor = IBus.MINOR_VERSION
    micro = IBus.MICRO_VERSION
    if (major, minor, micro) < tuple(map(int, (v.split('.')))):
        raise ValueError('Required ibus %s but version of ibus is ' \
                         '%d.%d.%d' % (v, major, minor, micro))


# Need to call IBus.init() before IBus.EngineSimple() is loaded.
# factory -> engine -> IBus.EngineSimple
try:
    # IBus.init() has not been needed here since IBus 1.5.32
    ibus_check_version("1.5.32")
except ValueError:
    import inspect
    parent_frame = inspect.currentframe().f_back
    # Call IBus.init() again from "from main import get_userhome" in engin.py.
    # The twice IBus.init() issue has been fixed since IBus 1.5.31 by
    # https://github.com/ibus/ibus/commit/9f50b46
    if parent_frame == None:
        IBus.init()

import factory


class IMApp:
    def __init__(self, exec_by_ibus):
        command_line = config.LIBEXECDIR + '/ibus-engine-anthy --ibus'
        self.__component = IBus.Component(name='org.freedesktop.IBus.Anthy',
                                          description='Anthy Component',
                                          version='0.1.0',
                                          license='GPL',
                                          author='Peng Huang <shawn.p.huang@gmail.com>',
                                          homepage='https://github.com/ibus/ibus/wiki',
                                          command_line=command_line,
                                          textdomain='ibus-anthy')
        engine = IBus.EngineDesc(name='anthy',
                                 longname='Anthy',
                                 description='Anthy Input Method',
                                 language='ja',
                                 license='GPL',
                                 author='Peng Huang <shawn.p.huang@gmail.com>',
                                 icon='ibus-anthy',
                                 layout=config.LAYOUT,
                                 symbol=config.SYMBOL_CHAR,
                                 rank=99)
        self.__component.add_engine(engine)
        self.__mainloop = GLib.MainLoop()
        self.__bus = IBus.Bus()
        self.__bus.connect('disconnected', self.__bus_disconnected_cb)
        self.__factory = factory.EngineFactory(self.__bus)
        if exec_by_ibus:
            self.__bus.request_name('org.freedesktop.IBus.Anthy', 0)
        else:
            self.__bus.register_component(self.__component)

    def run(self):
        self.__mainloop.run()

    def __bus_disconnected_cb(self, bus):
        self.__mainloop.quit()


def launch_engine(exec_by_ibus):
    IMApp(exec_by_ibus).run()

def get_userhome():
    if 'HOME' not in os.environ:
        import pwd
        userhome = pwd.getpwuid(os.getuid()).pw_dir
    else:
        userhome = os.environ['HOME']
    userhome = userhome.rstrip('/')
    return userhome

def resync_engine_file():
    user_config = path.join(get_userhome(), '.config',
                            'ibus-anthy', 'engines.xml')
    system_config = path.join(config.PKGDATADIR, 'engine', 'default.xml')
    if not path.exists(user_config):
        return
    if not path.exists(system_config):
        os.unlink(user_config)
        return

    # path.getmtime depends on the build time rather than install time.
    def __get_engine_file_version(engine_file):
        version_str = ''
        dom = xml.dom.minidom.parse(engine_file)
        elements = dom.getElementsByTagName('version')
        nodes = []
        if len(elements) > 0:
            nodes = elements[0].childNodes
        if len(nodes) > 0:
            version_str = nodes[0].data
        if version_str != '':
            version_str = version_str.strip()
        return version_str

    user_config_version = __get_engine_file_version(user_config)
    system_config_version = __get_engine_file_version(system_config)
    if system_config_version > user_config_version:
        import shutil
        shutil.copyfile(system_config, user_config)

def print_xml():
    user_config = os.path.join(get_userhome(), '.config',
                               'ibus-anthy', 'engines.xml')
    system_config = os.path.join(config.PKGDATADIR, 'engine', 'default.xml')
    xml = None
    for f in [user_config, system_config]:
        if os.path.exists(f):
            xml = f
            break
    if xml == None:
        print('Not exist: %s' % system_config, file=sys.stderr)
        return
    file = open(xml, 'r')
    print(file.read())
    file.close()

def print_help(out, v = 0):
    print('-i, --ibus             executed by ibus.', file=out)
    print('-h, --help             show this message.', file=out)
    print('-d, --daemonize        daemonize ibus.', file=out)
    print('-x, --xml              print engine xml.', file=out)
    sys.exit(v)

def main():
    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

    exec_by_ibus = False
    daemonize = False
    xml = False

    shortopt = 'ihdx'
    longopt = ['ibus', 'help', 'daemonize', 'xml']

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopt, longopt)
    except getopt.GetoptError as err:
        print_help(sys.stderr, 1)

    for o, a in opts:
        if o in ('-h', '--help'):
            print_help(sys.stdout)
        elif o in ('-d', '--daemonize'):
            daemonize = True
        elif o in ('-i', '--ibus'):
            exec_by_ibus = True
        elif o in ('-x', '--xml'):
            xml = True
        else:
            print('Unknown argument: %s' % o, file=sys.stderr)
            print_help(sys.stderr, 1)

    if daemonize:
        if os.fork():
            sys.exit()

    if xml:
        resync_engine_file()
        print_xml()
        return

    launch_engine(exec_by_ibus)

if __name__ == '__main__':
    main()
