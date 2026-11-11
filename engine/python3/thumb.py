# -*- coding: utf-8 -*-
# vim:set et sts=4 sw=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
# Copyright (c) 2010-2017 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2017 Red Hat, Inc.
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

__all__ = (
        'ThumbShiftKeyboard',
        'ThumbShiftSegment',
    )

import sys

from gi import require_version as gi_require_version
gi_require_version('GLib', '2.0')
gi_require_version('IBus', '1.0')

from gi.repository import GLib
from gi.repository import IBus

import segment

_THUMB_BASIC_METHOD = 'base'

_table_static = {
    'q': ['。', '',   'ぁ'],
    'w': ['か', 'が', 'え'],
    'e': ['た', 'だ', 'り'],
    'r': ['こ', 'ご', 'ゃ'],
    't': ['さ', 'ざ', 'れ'],

    'y': ['ら', 'よ', 'ぱ'],
    'u': ['ち', 'に', 'ぢ'],
    'i': ['く', 'る', 'ぐ'],
    'o': ['つ', 'ま', 'づ'],
    'p': ['，',  'ぇ', 'ぴ'],
    '@': ['、', '',   ''],
    '[': ['゛', '゜', ''],

    'a': ['う', '',   'を'],
    's': ['し', 'じ', 'あ'],
    'd': ['て', 'で', 'な'],
    'f': ['け', 'げ', 'ゅ'],
    'g': ['せ', 'ぜ', 'も'],

    'h': ['は', 'み', 'ば'],
    'j': ['と', 'お', 'ど'],
    'k': ['き', 'の', 'ぎ'],
    'l': ['い', 'ょ', 'ぽ'],
    ';': ['ん', 'っ', ''],

    'z': ['．',  '',   'ぅ'],
    'x': ['ひ', 'び', 'ー'],
    'c': ['す', 'ず', 'ろ'],
    'v': ['ふ', 'ぶ', 'や'],
    'b': ['へ', 'べ', 'ぃ'],

    'n': ['め', 'ぬ', 'ぷ'],
    'm': ['そ', 'ゆ', 'ぞ'],
    ',': ['ね', 'む', 'ぺ'],
    '.': ['ほ', 'わ', 'ぼ'],
    '/': ['・', 'ぉ', ''],

    '1': ['1',  '',   '？'],
    '2': ['2',  '',   '／'],
    '4': ['4',  '',   '「'],
    '5': ['5',  '',   '」'],

    '6': ['6',  '［',  ''],
    '7': ['7',  '］',  ''],
    '8': ['8',  '（',  ''],
    '9': ['9',  '）',  ''],
    '\\': ['￥', '',  ''],
}

_nicola_j_table_static = {
    ':': ['：', '',   ''],
    '@': ['、', '',   ''],
    '[': ['゛', '゜', ''],
    ']': ['」', '',   ''],
    '8': ['8',  '（', ''],
    '9': ['9',  '）', ''],
    '0': ['0',  '',   ''],
}

_nicola_a_table_static = {
    ':': ['：', '',   ''],
    '@': ['＠', '',   ''],
    '[': ['、', '',   ''],
    ']': ['゛', '゜', ''],
    '8': ['8',  '',   ''],
    '9': ['9',  '（', ''],
    '0': ['0',  '）', ''],
}

_nicola_f_table_static = {
    ':': ['、', '',   ''],
    '@': ['＠', '',   ''],
    '[': ['゛', '゜', ''],
    ']': ['」', '',   ''],
    '8': ['8',  '（', ''],
    '9': ['9',  '）', ''],
    '0': ['0',  '',   ''],
}

_kb231_j_fmv_table_static = {
    '3': ['3',  '',   '～'],
    '0': ['0',  '『', ''],
    '-': ['-',  '』', ''],
    '=': ['=',  '',   ''],
}

_kb231_a_fmv_table_static = {
    '3': ['3',  '',   '～'],
    '0': ['0',  '）', ''],
    '-': ['-',  '『', ''],
    '=': ['=',  '』', ''],
}

_kb231_f_fmv_table_static = {
    '3': ['3',  '',   '～'],
    '0': ['0',  '『', ''],
    '-': ['-',  '』', ''],
    '=': ['=',  '',   ''],
}

_kb611_j_fmv_table_static = {
    '`':  ['‘', '',   ''],
    '^':  ['々', '£',  ''],
    ':':  ['：', '',   ''],
    '@':  ['、', '¢',  ''],
    '[':  ['゛', '゜', ''],
    # keysyms are same and keycodes depend on the platforms.
    #'￥': [u'￥', u'¬',  u''],
    '\\': ['￥', '¦',  ''],
}

_kb611_a_fmv_table_static = {
    '`':  ['々', '',   '£'],
    ':':  ['：', '',   ''],
    '@':  ['＠', '',   ''],
    '[':  ['、', '¢',  ''],
    #'￥': [u'￥', u'¬',  u''],
    '\\': ['￥', '¦',  ''],
}

_kb611_f_fmv_table_static = {
    '`':  ['‘', '',   ''],
    '^':  ['々', '£',  ''],
    ':':  ['、', '¢',  ''],
    '@':  ['＠', '',   ''],
    '[':  ['゛', '゜', ''],
    #'￥': [u'￥', u'¬',  u''],
    '\\': ['￥', '¦',  ''],
}

_shift_table = {
    'H': 'ぱ',
    'X': 'ぴ',
    'V': 'ぷ',
    'B': 'ぺ',
    '>': 'ぽ',
}

table_static = {}
r_table_static = {}

for k in list(_table_static.keys()):
    table_static[ord(k)] = _table_static[k]
    for c in _table_static[k]:
        r_table_static[c] = k

kana_voiced_consonant_rule = {
    'か゛' : 'が',
    'き゛' : 'ぎ',
    'く゛' : 'ぐ',
    'け゛' : 'げ',
    'こ゛' : 'ご',
    'さ゛' : 'ざ',
    'し゛' : 'じ',
    'す゛' : 'ず',
    'せ゛' : 'ぜ',
    'そ゛' : 'ぞ',
    'た゛' : 'だ',
    'ち゛' : 'ぢ',
    'つ゛' : 'づ',
    'て゛' : 'で',
    'と゛' : 'ど',
    'は゛' : 'ば',
    'ひ゛' : 'び',
    'ふ゛' : 'ぶ',
    'へ゛' : 'べ',
    'ほ゛' : 'ぼ',
    'は゜' : 'ぱ',
    'ひ゜' : 'ぴ',
    'ふ゜' : 'ぷ',
    'へ゜' : 'ぺ',
    'ほ゜' : 'ぽ',
}

_UNFINISHED_HIRAGANA = set('かきくけこさしすせそたちつてとはひふへほ')

class ThumbShiftKeyboard:
    def __init__(self, prefs=None):
        self.__prefs = prefs
        self.__table = table_static
        self.__r_table = r_table_static
        self.__shift_table = {}
        self.__ls = 0
        self.__rs = 0
        self.__t1 = 0
        self.__t2 = 0
        self.__layout = 0
        self.__fmv_extension = 2
        self.__handakuten = False
        self.__thumb_typing_rule_method = None
        self.__init_thumb_typing_rule()
        self.__init_layout_table()
        if self.__prefs != None:
            self.reset()
            self.__reset_shift_table(False)

    def __init_thumb_typing_rule(self):
        prefs = self.__prefs
        if prefs == None:
            self.__thumb_typing_rule_method = None
            return
        method = prefs.get_value('thumb-typing-rule', 'method')
        if method == None:
            method = _THUMB_BASIC_METHOD
        self.__thumb_typing_rule_method = method
        keymap = prefs.get_value('thumb-typing-rule', 'list')
        if self.__thumb_typing_rule_method not in keymap.keys():
            self.__thumb_typing_rule_method = None

    def __init_layout_table(self):
        if self.__table != {}:
            self.__table.clear()
        if self.__r_table != {}:
            self.__r_table.clear()
        method = self.__thumb_typing_rule_method
        if method != None:
            prefs = self.__prefs
            keymap = prefs.get_value('thumb-typing-rule', 'list')[method]
            for k in keymap.keys():
                value = keymap.get(k)
                ch = prefs.typing_from_config_key(k)
                if ch == '':
                    continue
                self.__set_bus_table(ch, value)
        else:
            for k in list(_table.keys()):
                self.__table[ord(k)] = _table_static[k]
                for c in _table_static[k]:
                    self.__r_table[c] = k

    def __set_bus_table(self, key, value):
        prefs = self.__prefs
        if value == None or len(value) != 3:
            return
        if value[0] == '' and \
                value[1] == '' and value[2] == '':
            return
        self.__table[ord(key)] = value
        for c in value:
            self.__r_table[c] = key

    def __reset_layout_table(self, init,
                             j_table_label, j_table,
                             a_table_label, a_table,
                             f_table_label, f_table):
        if init:
            self.__init_layout_table()
        method = None
        sub_table = None
        if self.__layout == 0:
            method = j_table_label
            sub_table = j_table
        elif self.__layout == 1:
            method = a_table_label
            sub_table = a_table
        elif self.__layout == 2:
            method = f_table_label
            sub_table = f_table
        if method == None or sub_table == None:
            return
        method = self.__thumb_typing_rule_method
        if method != None:
            prefs = self.__prefs
            keymap = prefs.get_value('thumb-typing-rule', 'list')[method]
            for k in keymap.keys():
                value = keymap.get(k)
                ch = prefs.typing_from_config_key(k)
                if ch == '':
                    continue
                self.__set_bus_table(ch, value)
        else:
            for k in list(sub_table.keys()):
                self.__table[ord(str(k))] = sub_table[k]
                for c in sub_table[k]:
                    self.__r_table[c] = k

    def __reset_extension_table(self, init):
        self.__reset_layout_table(init,
                                  'nicola_j_table',
                                  _nicola_j_table_static,
                                  'nicola_a_table',
                                  _nicola_a_table_static,
                                  'nicola_f_table',
                                  _nicola_f_table_static)
        if self.__fmv_extension == 0:
            return
        if self.__fmv_extension >= 1:
            self.__reset_layout_table(False,
                                      'kb231_j_fmv_table',
                                      _kb231_j_fmv_table_static,
                                      'kb231_a_fmv_table',
                                      _kb231_a_fmv_table_static,
                                      'kb231_f_fmv_table',
                                      _kb231_f_fmv_table_static)
        if self.__fmv_extension >= 2:
            self.__reset_layout_table(False,
                                      'kb611_j_fmv_table',
                                      _kb611_j_fmv_table_static,
                                      'kb611_a_fmv_table',
                                      _kb611_a_fmv_table_static,
                                      'kb611_f_fmv_table',
                                      _kb611_f_fmv_table_static)

    def __reset_shift_table(self, init):
        self.__reset_extension_table(init)
        if self.__handakuten:
            for k in list(_shift_table.keys()):
                self.__shift_table[ord(k)] = _shift_table[k]
                self.__r_table[_shift_table[k]] = k
        elif self.__shift_table != {}:
            for k in list(_shift_table.keys()):
                if ord(k) in self.__shift_table:
                    del self.__shift_table[ord(k)]
                if _shift_table[k] in self.__r_table:
                    del self.__r_table[_shift_table[k]]

    def __s_to_key_raw(self, s):
        keyval = IBus.keyval_from_name(s.split('+')[-1])
        s = s.lower()
        state = ('shift+' in s and IBus.ModifierType.SHIFT_MASK or 0) | (
                 'ctrl+' in s and IBus.ModifierType.CONTROL_MASK or 0) | (
                 'alt+' in s and IBus.ModifierType.MOD1_MASK or 0)
        return (keyval, state)

    def __get_xkb_layout(self):
        # Until Gdk.property_get is fixed
        '''
        # Move importing Gdk into ThumbShiftKeyboard from the header
        # because ibus-engine-anthy --xml does not requre to open X.
        try:
            from gi.repository import Gdk
            get_default_root_window = Gdk.get_default_root_window
            property_get = Gdk.property_get
            intern = Gdk.Atom.intern
        except ImportError:
            get_default_root_window = lambda : None
            property_get = lambda : None
            intern = lambda : None
        except RuntimeError:
            # Do we support the engine without display?
            print >> sys.stderr, "Gdk couldn't be initialized"
            print >> sys.stderr, 'Could not open display'
            get_default_root_window = lambda : None
            property_get = lambda : None
            intern = lambda : None

        root_window = get_default_root_window()
        if not root_window:
            return 0
        xkb_rules_names = intern('_XKB_RULES_NAMES', False)
        xa_string = intern('STRING', False)
        try:
            prop = property_get(root_window,
                                xkb_rules_names, xa_string,
                                0, 1024, 0)[3]
            layout_list = prop.split('\0')
        except TypeError:
            print >> sys.stderr, \
              'This problem is fixed in the latest gobject-introspection'
            print >> sys.stderr, \
              'https://bugzilla.gnome.org/show_bug.cgi?id=670509'
            return 0
        layout = 0
        for data in layout_list:
            if data == 'jp':
                layout = 0
            elif data == 'us':
                layout = 1
            elif data.find('japan:nicola_f_bs') >= 0:
                layout = 2
            elif data.find('japan:') >= 0:
                layout = 0
        return layout
        '''

        layout = 0
        argv = ['setxkbmap', '-query']
        (ret, std_out, std_error, exit_status) = \
                GLib.spawn_sync(None, argv, None,
                                GLib.SpawnFlags.SEARCH_PATH_FROM_ENVP,
                                None, None)
        if not ret:
            print(std_error.decode('utf-8'), file=sys.stderr)
            return layout
        for line in std_out.decode('utf-8').split('\n'):
            if line.startswith('layout:'):
                data = line.split()[1]
                if data == 'jp':
                    layout = 0
                elif data == 'us':
                    layout = 1
            elif line.startswith('options:'):
                data = line.split()[1]
                if data.find('japan:nicola_f_bs') >= 0:
                    layout = 2
                elif data.find('japan:') >= 0:
                    layout = 0
        return layout

    def __reset_layout_and_handakuten(self):
        mode = self.__prefs.get_value('thumb', 'keyboard-layout-mode')
        layout = 0
        if mode == 1:
            layout = self.__get_xkb_layout()
        else:
            layout = self.__prefs.get_value('thumb', 'keyboard-layout')
        self.set_layout(layout)

        fmv_extension = self.__prefs.get_value('thumb', 'fmv-extension')
        self.set_fmv_extension(fmv_extension)
        handakuten = self.__prefs.get_value('thumb', 'handakuten')
        self.set_handakuten(handakuten)

    def reset(self):
        s = self.__prefs.get_value('thumb', 'ls')
        ls, state = self.__s_to_key_raw(s)
        if ls == 0xffffff:
            ls = IBus.KEY_Muhenkan
        self.set_ls(ls)

        s = self.__prefs.get_value('thumb', 'rs')
        rs, state = self.__s_to_key_raw(s)
        if rs == 0xffffff:
            rs = IBus.KEY_Henkan
        self.set_rs(rs)

        t1 = self.__prefs.get_value('thumb', 't1')
        t2 = self.__prefs.get_value('thumb', 't2')
        self.set_t1(t1)
        self.set_t2(t2)

        GLib.idle_add(self.__reset_layout_and_handakuten,
                      priority = GLib.PRIORITY_LOW)

    def get_ls(self):
        return self.__ls

    def set_ls(self, ls):
        self.__ls = ls

    def get_rs(self):
        return self.__rs

    def set_rs(self, rs):
        self.__rs = rs

    def get_t1(self):
        return self.__t1

    def set_t1(self, t1):
        self.__t1 = t1

    def get_t2(self):
        return self.__t2

    def set_t2(self, t2):
        self.__t2 = t2

    def get_layout(self):
        return self.__layout

    def set_layout(self, layout):
        if self.__layout == layout:
            return
        self.__layout = layout
        self.__reset_shift_table(True)

    def get_fmv_extension (self):
        return self.__fmv_extension

    def set_fmv_extension (self, fmv_extension):
        if self.__fmv_extension == fmv_extension:
            return
        self.__fmv_extension = fmv_extension
        self.__reset_shift_table(True)

    def get_handakuten(self):
        return self.__handakuten

    def set_handakuten(self, handakuten):
        if self.__handakuten == handakuten:
            return
        self.__handakuten = handakuten
        self.__reset_shift_table(True)

    def get_char(self, key, fallback=None):
        return self.__table.get(key, fallback)

    def get_chars(self):
        return list(self.__table.keys())

    def get_r_char(self, key, fallback=None):
        return self.__r_table.get(key, fallback)

    def get_r_chars(self):
        return list(self.__r_table.keys())

    def get_shift_char(self, key, fallback=None):
        return self.__shift_table.get(key, fallback)

    def get_shift_chars(self):
        return list(self.__shift_table.keys())


class ThumbShiftSegment(segment.Segment):
    _prefs = None
    _thumb_typing_rule_section_base = None
    _thumb_typing_rule_section = None
    _r_table = {}

    def __init__(self, enchars='', jachars=''):
        if not jachars:
            if '!' <= enchars <= '~':
                jachars = segment.unichar_half_to_full(enchars)
            else:
                jachars = enchars
                enchars = self._r_table.get(jachars, '')
        super(ThumbShiftSegment, self).__init__(enchars, jachars)

    @classmethod
    def INIT_THUMB_TYPING_RULE(cls, prefs):
        cls._prefs = prefs
        if prefs == None:
            cls._thumb_typing_rule_section = None
            return
        method = prefs.get_value('thumb-typing-rule', 'method')
        if method == None:
            method = _THUMB_BASIC_METHOD
        cls._thumb_typing_rule_method = method
        keymap = prefs.get_value('thumb-typing-rule', 'list')
        if cls._thumb_typing_rule_method not in keymap.keys():
            cls._thumb_typing_rule_method = None
        cls._init_layout_table()

    @classmethod
    def _init_layout_table(cls):
        if cls._r_table != {}:
            cls._r_table.clear()
        method = cls._thumb_typing_rule_method
        if method != None:
            prefs = cls._prefs
            keymap = prefs.get_value('thumb-typing-rule', 'list')[method]
            for k in keymap.keys():
                value = keymap.get(k)
                ch = prefs.typing_from_config_key(k)
                if ch == '':
                    continue
                cls._set_bus_table(ch, value)
        else:
            for k in list(_table.keys()):
                for c in _table_static[k]:
                    cls._r_table[c] = k

    @classmethod
    def _set_bus_table(cls, key, value):
        prefs = cls._prefs
        if value == None or len(value) != 3:
            return
        if value[0] == '' and \
                value[1] == '' and value[2] == '':
            return
        for c in value:
            cls._r_table[c] = key

    def is_finished(self):
        return not (self._jachars in _UNFINISHED_HIRAGANA)

    def append(self, enchar):
        if enchar == '\0' or enchar == '':
            return []
        text = self._jachars + enchar
        jachars = kana_voiced_consonant_rule.get(text, None)
        if jachars:
            self._enchars = self._enchars + self._r_table.get(enchar, '')
            self._jachars = jachars
            return []
        return [ThumbShiftSegment(enchar)]

    def prepend(self, enchar):
        if enchar == '\0' or enchar == '':
            return []
        if self._jachars == '':
            if 0x21 <= enchars <= 0x7e:
                self._enchars = enchar
                self._jachars = segment.unichar_half_to_full(enchars)
            else:
                self._enchars = self._r_table.get(enchar, '')
                self._jachars = enchar
            return []
        return [ThumbShiftSegment(enchar)]

    def pop(self, index=-1):
        self._enchars = ''
        self._jachars = ''
        return

