# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
# Copyright (c) 2010-2014 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2014 Red Hat, Inc.
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

import sys

from gi.repository import GLib
from gi.repository import IBus

class Prefs(object):
    _prefix = 'engine/dummy'

    def __init__(self, bus=None, config=None):
        self.default = {}
        self.modified = {}
        self.new = {}
        self.__no_key_warning = False

        # self._config is used by AnthyPrefs .
        self._config = config if config else \
                       bus.get_config() if bus else  \
                       IBus.Bus().get_config()

        # ibus_config_get_values enhances the performance.
        self.__has_config_get_values = False

        if self._config != None:
            self.__has_config_get_values = hasattr(self._config, 'get_values')
        else:
            self.printerr(
                'ibus-config is not running or bus address is not correct.')

    def __log_handler(self, domain, level, message, data):
        if not data:
            return
        GLib.log_default_handler(domain, level, message, '')

    def variant_to_value(self, variant):
        if type(variant) != GLib.Variant:
            return variant
        type_string = variant.get_type_string()
        if type_string == 's':
            return variant.get_string()
        elif type_string == 'i':
            return variant.get_int32()
        elif type_string == 'b':
            return variant.get_boolean()
        elif type_string == 'as':
            # Use unpack() instead of dup_strv() in python.
            # In the latest pygobject3 3.3.4 or later, g_variant_dup_strv
            # returns the allocated strv but in the previous release,
            # it returned the tuple of (strv, length)
            return variant.unpack()
        else:
            self.printerr('Unknown variant type:', type_string)
            sys.abrt()
        return variant

    def set_no_key_warning(self, no_key_warning):
        if no_key_warning and hasattr(IBus, 'unset_log_handler'):
            self.__no_key_warning = True
        else:
            self.__no_key_warning = False

    def keys(self, section):
        return self.default[section].keys()

    def sections(self):
        return self.default.keys()

    def set_new_section(self, section):
        self.default.setdefault(section, {})

    def set_new_key(self, section, key):
        self.default[section].setdefault(key)

    def get_value(self, section, key):
        try:
            return self.new[section][key]
        except:
            try:
                return self.modified[section][key]
            except:
                return self.default[section][key]

    def get_value_direct(self, section, key, default=None):
        if self._config == None:
            return default

        s = section
        section = '/'.join(
            [s for s in '/'.join([self._prefix, section]).split('/') if s])
        try:
            if self.__no_key_warning:
                IBus.set_log_handler(False)
            variant = self._config.get_value(section, key)
            if self.__no_key_warning:
                IBus.unset_log_handler()
            return self.variant_to_value(variant)
        except:
            return default

    def set_value(self, section, key, value):
        if section not in self.sections():
            self.set_new_section(section)
        if key not in self.keys(section):
            self.set_new_key(section, key)
        self.default[section][key]
        self.new.setdefault(section, {})[key] = value

    def fetch_all(self):
        for s in self.sections():
            self.fetch_section(s)

    def fetch_section(self, section):
        if self._config == None:
            return

        if not self.__has_config_get_values:
            for k in self.keys(section):
                self.fetch_item(section, k)
            return

        s = '/'.join(
            [s for s in '/'.join([self._prefix, section]).split('/') if s])
        variant = self._config.get_values(s)
        for key in variant.keys():
            v = variant[key]
            # FIXME: ibus-dconf converts the keys.
            #if key.find('_') >= 0:
            #    key = key.replace('_', '-')
            if section == 'common':
                if key == 'show_input_mode':
                    key = 'show-input-mode'
                elif key == 'show_typing_method':
                    key = 'show-typing-method'
                elif key == 'show_segment_mode':
                    key = 'show-segment-mode'
                elif key == 'show_dict_mode':
                    key = 'show-dict-mode'
                elif key == 'show_dict_config':
                    key = 'show-dict-config'
                elif key == 'show_preferences':
                    key = 'show-preferences'
                elif key == 'show_input_mode_icon':
                    key = 'show-input-mode-icon'
                elif key == 'icon_str_rgba':
                    key = 'icon-str-rgba'
            self.modified.setdefault(section, {})[key] = v if v != [''] else []

    def fetch_item(self, section, key, readonly=False):
        if self._config == None:
            return

        s = '/'.join(
            [s for s in '/'.join([self._prefix, section]).split('/') if s])
        try:
            v = None
            # gobject-introspection has a bug.
            # https://bugzilla.gnome.org/show_bug.cgi?id=670509
            # GLib.log_set_handler("IBUS", GLib.LogLevelFlags.LEVEL_MASK,
            #                      self.__log_handler, False)
            if self.__no_key_warning:
                IBus.set_log_handler(False)
            variant = self._config.get_value(s, key)
            if self.__no_key_warning:
                IBus.unset_log_handler()
            v = self.variant_to_value(variant)
        except:
            v = None
        if readonly:
            return v != None
        if v != None:
            self.modified.setdefault(section, {})[key] = v if v != [''] else []
        return True

    def commit_all(self):
        for s in self.new.keys():
            self.commit_section(s)

    def commit_section(self, section):
        if section in self.new:
            for k in self.new[section].keys():
                self.commit_item(section, k)

    def commit_item(self, section, key):
        if section in self.new and key in self.new[section]:
            s = '/'.join(
                [s for s in '/'.join([self._prefix, section]).split('/') if s])
            v = self.new[section][key]
            if v == []:
                v = ['']
            variant = None
            if type(v) == str:
                variant = GLib.Variant.new_string(v)
            elif type(v) == int:
                variant = GLib.Variant.new_int32(v)
            elif type(v) == bool:
                variant = GLib.Variant.new_boolean(v)
            elif type(v) == list:
                variant = GLib.Variant.new_strv(v)
            if variant == None:
                self.printerr('Unknown value type:', type(v))
                sys.abrt()
            if self._config != None:
                self._config.set_value(s, key, variant)
            self.modified.setdefault(section, {})[key] = v
            del(self.new[section][key])

    def undo_all(self):
        self.new.clear()

    def undo_section(self, section):
        try:
            del(self.new[section])
        except:
            pass

    def undo_item(self, section, key):
        try:
            del(self.new[section][key])
        except:
            pass

    def set_default_all(self):
        for s in self.sections():
            self.set_default_section(s)

    def set_default_section(self, section):
        for k in self.keys(section):
            self.set_default_item(section, k)

    def set_default_item(self, section, key):
        try:
            if key in self.modified[section] or key in self.new[section]:
                self.new[section][key] = self.default[section][key]
        except:
            pass

    # Convert DBus.String to str
    # sys.getdefaultencoding() == 'utf-8' with pygtk2 but
    # sys.getdefaultencoding() == 'ascii' with gi gtk3
    # so the simple str(unicode_string) causes an error and need to use
    # unicode_string.encode('utf-8') instead.
    def str(self, uni):
        if uni == None:
            return None
        if type(uni) == str:
            return uni
        if type(uni) == unicode:
            return uni.encode('utf-8')
        return str(uni)

    # The simple unicode(string) causes an error and need to use
    # unicode(string, 'utf-8') instead.
    def unicode(self, string):
        if string == None:
            return None
        if type(string) == unicode:
            return string
        return unicode(string, 'utf-8')

    # If the parent process exited, the std io/out/error will be lost.
    @staticmethod
    def printerr(sentence):
        try:
            print >> sys.stderr, sentence
        except IOError:
            pass

