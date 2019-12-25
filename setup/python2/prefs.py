# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
# Copyright (c) 2010-2019 Takao Fujiwara <takao.fujiwara1@gmail.com>
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

import sys

from gi import require_version as gi_require_version
gi_require_version('Gio', '2.0')
gi_require_version('GLib', '2.0')
gi_require_version('IBus', '1.0')

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import IBus

class DictItem():
    def __init__(self,
                 id='',
                 short_label='',
                 long_label='',
                 icon='',
                 is_system=False,
                 preview_lines=-1,
                 embed=False,
                 single=True,
                 reverse=False,
                 encoding='utf-8'):
        self.id = id
        self.short_label = short_label
        self.long_label = long_label
        self.icon = icon
        self.is_system = is_system
        self.preview_lines = preview_lines
        self.embed = embed
        self.single = single
        self.reverse = reverse
        self.encoding = encoding

    def __str__(self):
        retval = ('id:', self.id,
              'short-label:', self.short_label,
              'long-label:', self.long_label,
              'icon:', self.icon,
              'is-system:', self.is_system,
              'preview-lines:', self.preview_lines,
              'embed:', self.embed,
              'single:', self.single,
              'reverse:', self.reverse,
              'encoding:', self.encoding)
        return str(retval)

    @classmethod
    def serialize(cls, dict_item):
        builder = GLib.VariantBuilder(GLib.VariantType('r'))
        builder.add_value(GLib.Variant.new_string(dict_item.id))
        builder.add_value(GLib.Variant.new_string(dict_item.short_label))
        builder.add_value(GLib.Variant.new_string(dict_item.long_label))
        builder.add_value(GLib.Variant.new_string(dict_item.icon))
        builder.add_value(GLib.Variant.new_boolean(dict_item.is_system))
        builder.add_value(GLib.Variant.new_int32(dict_item.preview_lines))
        builder.add_value(GLib.Variant.new_boolean(dict_item.embed))
        builder.add_value(GLib.Variant.new_boolean(dict_item.single))
        builder.add_value(GLib.Variant.new_boolean(dict_item.reverse))
        builder.add_value(GLib.Variant.new_string(dict_item.encoding))
        return builder.end()

class Prefs(GObject.GObject):
    __gsignals__ = {
        'changed' : (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, GLib.Variant)),
        }

    def __init__(self):
        super(Prefs, self).__init__()
        self.__cache = {}
        self.__settings = {}
        self.__schema_prefix = 'org.freedesktop.ibus.engine.anthy.'
        self.__schema_sections = ['common',
                                  'shortcut',
                                  'romaji-typing-rule',
                                  'kana-typing-rule',
                                  'thumb-typing-rule',
                                  'thumb',
                                  'dict']
        for section in self.__schema_sections:
            self.__settings[section] = Gio.Settings(
                    schema=self.__schema_prefix + section)
            self.__settings[section].connect('changed',
                                             self.__settings_on_changed)
        self.__core_cache = {}
        self.__core_settings = {}
        self.__core_schema_prefix = 'org.freedesktop.ibus.'
        self.__core_schema_sections = ['general']
        for section in self.__core_schema_sections:
            self.__core_settings[section] = Gio.Settings(
                    schema=self.__core_schema_prefix + section)
            self.__core_settings[section].connect('changed',
                                             self.__settings_on_changed)

    def __settings_on_changed(self, settings, key):
        schema = settings.props.schema
        is_anthy = False
        if schema.startswith(self.__schema_prefix):
            section = settings.props.schema[len(self.__schema_prefix):]
            variant_value = self.__settings[section].get_value(key)
            variant_key = self.__cache.get(section)
            is_anthy = True
        else:
            section = settings.props.schema[len(self.__core_schema_prefix):]
            variant_value = self.__core_settings[section].get_value(key)
            variant_key = self.__core_cache.get(section)
        if variant_key == None:
            variant_key = {}
        variant_key[key] = variant_value
        if is_anthy:
            self.__cache[section] = variant_key
        else:
            self.__core_cache[section] = variant_key
            section = 'core:' + section
        self.emit('changed', section, key, variant_value)

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
        elif type_string == 'v':
            return variant.unpack()
        elif len(type_string) > 0 and type_string[0] == 'a':
            # Use unpack() instead of dup_strv() in python.
            # In the latest pygobject3 3.3.4 or later, g_variant_dup_strv
            # returns the allocated strv but in the previous release,
            # it returned the tuple of (strv, length)
            return variant.unpack()
        else:
            self.printerr('Unknown variant type:', type_string)
            sys.abrt()
        return variant

    def variant_from_value(self, value):
        variant = None
        if type(value) == str:
            variant = GLib.Variant.new_string(value)
        elif type(value) == int:
            variant = GLib.Variant.new_int32(value)
        elif type(value) == bool:
            variant = GLib.Variant.new_boolean(value)
        elif type(value) == list:
            variant = GLib.Variant.new_strv(value)
        if variant == None:
            self.printerr('Unknown value type: %s' % type(value))
        return variant

    def get_variant(self, section, key):
        is_core = section.startswith('core:')
        if is_core:
            section = section[len('core:'):]
            variant_key = self.__core_cache.get(section)
        else:
            variant_key = self.__cache.get(section)
        if variant_key != None:
            variant_value = variant_key.get(key)
            if variant_value != None:
                return variant_value
        if is_core:
            variant_value = self.__core_settings[section].get_value(key)
        else:
            variant_value = self.__settings[section].get_value(key)
        if variant_key == None:
            variant_key = {}
        variant_key[key] = variant_value
        if is_core:
            self.__core_cache[section] = variant_key
        else:
            self.__cache[section] = variant_key
        return variant_value

    def get_default_variant(self, section, key):
        return  self.__settings[section].get_default_value(key)

    def get_readable_value(self, section, key, variant):
        value = self.variant_to_value(variant)
        if section == 'dict' and key == 'list':
            dicts = {}
            for item in value:
                dict_item = DictItem(*item)
                dicts[dict_item.id] = dict_item
            value = dicts
        if section == 'dict' and key == 'template':
            value = DictItem(*value)
        return value

    def get_value(self, section, key):
        variant = self.get_variant(section, key)
        return self.get_readable_value(section, key, variant)

    def get_default_value(self, section, key):
        variant = self.get_default_variant(section, key)
        return self.get_readable_value(section, key, variant)

    def set_variant(self, section, key, variant):
        self.__settings[section].set_value(key, variant)
        self.__settings[section].apply()

    def set_value(self, section, key, value):
        variant = self.variant_from_value(value)
        if variant == None:
            return
        self.set_variant(section, key, variant)

    def set_list_item(self, section, key, item, values):
        variant = self.get_variant(section, key)
        if variant == None:
            printerrr('%s:%s does not exist' % (section, key))
            return
        if section == 'shortcut':
            variant_dict = GLib.VariantDict(variant)
            array = []
            for value in values:
                array.append(GLib.Variant.new_string(value))
            varray = GLib.Variant.new_array(GLib.VariantType('s'), array)
            variant_dict.insert_value(item, varray)
            # GVariantDict uses GHashTable internally and
            # GVariantDict.end() does not support the order.
            self.set_variant(section, key, variant_dict.end())
            return
        if section == 'romaji-typing-rule' or \
           section == 'kana-typing-rule' or \
           section == 'thumb-typing-rule':
            (method, keymap_key) = item
            variant_dict = GLib.VariantDict(variant)
            keymap = variant_dict.lookup_value(method, None)
            keymap_dict = GLib.VariantDict(keymap)
            if section == 'thumb-typing-rule':
                array = []
                for value in values:
                    array.append(GLib.Variant.new_string(value))
                vvalue = GLib.Variant.new_array(GLib.VariantType('s'), array)
            else:
                vvalue = GLib.Variant.new_string(values)
            keymap_dict.insert_value(keymap_key, vvalue)
            keymap = keymap_dict.end()
            variant_dict.insert_value(method, keymap)
            self.set_variant(section, key, variant_dict.end())
            return
        if section == 'dict' and key == 'files':
            variant_dict = GLib.VariantDict(variant)
            array = []
            for value in values:
                array.append(GLib.Variant.new_string(value))
            varray = GLib.Variant.new_array(GLib.VariantType('s'), array)
            variant_dict.insert_value(item, varray)
            self.set_variant(section, key, variant_dict.end())
            return
        if section == 'dict' and key == 'list':
            array = []
            has_item = False
            for v in variant:
                dict_item = DictItem(*v)
                if dict_item.id == values.id:
                    array.append(GLib.Variant.new_variant(
                            DictItem.serialize(values)))
                    has_item = True
                else:
                    array.append(GLib.Variant.new_variant(
                            DictItem.serialize(dict_item)))
            if not has_item:
                array.append(GLib.Variant.new_variant(DictItem.serialize(values)))
            varray = GLib.Variant.new_array(GLib.VariantType('v'), array)
            self.set_variant(section, key, varray)
            return

    def delete_list_item(self, section, key, item):
        variant = self.get_variant(section, key)
        if variant == None:
            printerrr('%s:%s does not exist' % (section, key))
            return
        if section == 'romaji-typing-rule' or \
           section == 'kana-typing-rule' or \
           section == 'thumb-typing-rule':
            (method, keymap_key) = item
            variant_dict = GLib.VariantDict(variant)
            keymap = variant_dict.lookup_value(method, None)
            keymap_dict = GLib.VariantDict(keymap)
            keymap_dict.remove(keymap_key)
            keymap = keymap_dict.end()
            variant_dict.insert_value(method, keymap)
            self.set_variant(section, key, variant_dict.end())
            return
        if section == 'dict' and key == 'files':
            variant_dict = GLib.VariantDict(variant)
            variant_dict.remove(item)
            self.set_variant(section, key, variant_dict.end())
            return
        if section == 'dict' and key == 'list':
            array = []
            for v in variant:
                dict_item = DictItem(*v)
                if dict_item.id == item:
                    continue
                else:
                    array.append(GLib.Variant.new_variant(
                            DictItem.serialize(dict_item)))
            varray = GLib.Variant.new_array(GLib.VariantType('v'), array)
            self.set_variant(section, key, varray)
            return

    def bind(self, section, key, object, property, flags):
        self.__settings[section].bind(key, object, property, flags)

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

