# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2025 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2017 Red Hat, Inc.
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
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys

from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')

from gi.repository import IBus

import _config as config
import engine


class EngineFactory(IBus.Factory):
    __gtype_name__ = 'IBusFactoryAnthy'
    FACTORY_PATH = '/com/redhat/IBus/engines/Anthy/Factory'
    ENGINE_PATH = '/com/redhat/IBus/engines/Anthy/Engine'
    NAME = 'Anthy'
    LANG = 'ja'
    ICON = config.PKGDATADIR + '/icons/ibus-anthy.png'
    AUTHORS = 'Huang Peng <shawn.p.huang@gmail.com>'
    CREDITS = 'GPLv2'

    def __init__(self, bus):
        self.__bus = bus
        engine.Engine.CONFIG_RELOADED()
        super(EngineFactory, self).__init__(object_path=IBus.PATH_FACTORY,
                                            connection=bus.get_connection())

        self.__id = 0

        bus.get_connection().signal_subscribe('org.freedesktop.DBus',
                                              'org.freedesktop.DBus',
                                              'NameOwnerChanged',
                                              '/org/freedesktop/DBus',
                                              None,
                                              0,
                                              self.__name_owner_changed_cb,
                                              bus)

    def do_create_engine(self, engine_name):
        if engine_name == 'anthy':
            self.__id += 1
            return engine.Engine(self.__bus, '%s/%d' % (self.ENGINE_PATH, self.__id))

        return super(EngineFactory, self).do_create_engine(engine_name)

    def __name_owner_changed_cb(self, connection, sender_name, object_path,
                                interface_name, signal_name, parameters,
                                user_data):
        if signal_name == 'NameOwnerChanged':
            engine.Engine.CONFIG_RELOADED()
