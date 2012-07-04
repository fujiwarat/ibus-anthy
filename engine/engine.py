# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2012 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2012 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from os import environ, path
import signal
import sys
from gettext import dgettext

try:
    from locale import getpreferredencoding
except:
    pass

from gi.repository import GObject
from gi.repository import IBus

try:
    from gi.repository import Gtk
    clipboard_get = Gtk.Clipboard.get
except ImportError:
    clipboard_get = lambda a : None

from gi.repository import Anthy
NTH_UNCONVERTED_CANDIDATE = Anthy.NTH_UNCONVERTED_CANDIDATE
NTH_KATAKANA_CANDIDATE = Anthy.NTH_KATAKANA_CANDIDATE
NTH_HIRAGANA_CANDIDATE = Anthy.NTH_HIRAGANA_CANDIDATE
NTH_HALFKANA_CANDIDATE = Anthy.NTH_HALFKANA_CANDIDATE

import _config as config
from tables import *
import jastring
from segment import unichar_half_to_full

sys.path.append(path.join(config.PKGDATADIR, 'setup'))
from anthyprefs import AnthyPrefs

_  = lambda a : dgettext('ibus-anthy', a)
N_ = lambda a : a
UN = lambda a : unicode(a, 'utf-8')

INPUT_MODE_HIRAGANA, \
INPUT_MODE_KATAKANA, \
INPUT_MODE_HALF_WIDTH_KATAKANA, \
INPUT_MODE_LATIN, \
INPUT_MODE_WIDE_LATIN = range(5)

CONV_MODE_OFF, \
CONV_MODE_ANTHY, \
CONV_MODE_HIRAGANA, \
CONV_MODE_KATAKANA, \
CONV_MODE_HALF_WIDTH_KATAKANA, \
CONV_MODE_LATIN_0, \
CONV_MODE_LATIN_1, \
CONV_MODE_LATIN_2, \
CONV_MODE_LATIN_3, \
CONV_MODE_WIDE_LATIN_0, \
CONV_MODE_WIDE_LATIN_1, \
CONV_MODE_WIDE_LATIN_2, \
CONV_MODE_WIDE_LATIN_3, \
CONV_MODE_PREDICTION = range(14)

SEGMENT_DEFAULT         = 0
SEGMENT_SINGLE          = 1 << 0
SEGMENT_IMMEDIATE       = 1 << 1

CLIPBOARD_RECONVERT = range(1)

LINK_DICT_EMBEDDED, \
LINK_DICT_SINGLE = range(2)

IMPORTED_EMBEDDED_DICT_DIR = 'imported_words_default.d'
IMPORTED_EMBEDDED_DICT_PREFIX = 'ibus__'
IMPORTED_SINGLE_DICT_PREFIX = 'imported_words_ibus__'

if not hasattr(IBus, 'KEY_plus'):
    IBus.KEY_plus = IBus.plus
    IBus.KEY_period = IBus.period
    IBus.KEY_slash = IBus.slash
    IBus.KEY_Return = IBus.Return
    IBus.KEY_equal = IBus.equal
    IBus.KEY_asterisk = IBus.asterisk
    IBus.KEY_comma = IBus.comma
    IBus.KEY_space = IBus.space
    IBus.KEY_minus = IBus.minus
    IBus.KEY_exclam = IBus.exclam
    IBus.KEY_asciitilde = IBus.asciitilde
    IBus.KEY_yen = IBus.yen
    IBus.KEY_A = IBus.A
    IBus.KEY_Z = IBus.Z
    IBus.KEY_a = IBus.a
    IBus.KEY_z = IBus.z
    IBus.KEY_0 = 48 #IBus.0
    IBus.KEY_KP_Add = IBus.KP_Add
    IBus.KEY_KP_Decimal  = IBus.KP_Decimal
    IBus.KEY_KP_Divide = IBus.KP_Divide
    IBus.KEY_KP_Enter = IBus.KP_Enter
    IBus.KEY_KP_Equal = IBus.KP_Equal
    IBus.KEY_KP_Multiply = IBus.KP_Multiply
    IBus.KEY_KP_Separator = IBus.KP_Separator
    IBus.KEY_KP_Space = IBus.KP_Space
    IBus.KEY_KP_Subtract = IBus.KP_Subtract

KP_Table = {}
for s in dir(IBus):
    if s.startswith('KEY_KP_'):
        v = IBus.keyval_from_name(s[7:])
        if v:
            KP_Table[IBus.keyval_from_name(s[4:])] = v
for k, v in zip(['KEY_KP_Add', 'KEY_KP_Decimal', 'KEY_KP_Divide', 'KEY_KP_Enter',
                 'KEY_KP_Equal', 'KEY_KP_Multiply', 'KEY_KP_Separator',
                 'KEY_KP_Space', 'KEY_KP_Subtract'],
                ['KEY_plus', 'KEY_period', 'KEY_slash', 'KEY_Return',
                 'KEY_equal', 'KEY_asterisk', 'KEY_comma',
                 'KEY_space', 'KEY_minus']):
    KP_Table[getattr(IBus, k)] = getattr(IBus, v)

# IBus.EngineSimple is not available in ibus 1.4
class Engine(IBus.Engine):
    __typing_mode = jastring.TYPING_MODE_ROMAJI

    __setup_pid = 0
    __prefs = None
    __keybind = {}
    __thumb = None

    def __init__(self, bus, object_path):
        super(Engine, self).__init__(connection=bus.get_connection(),
                                     object_path=object_path)

        # create anthy context
        self.__context = Anthy.GContext()
        self.__context.set_encoding(Anthy.UTF8_ENCODING)

        # init state
        self.__idle_id = 0
        self.__input_mode = INPUT_MODE_HIRAGANA
        self.__segment_mode = SEGMENT_DEFAULT
        self.__dict_mode = 0
        self.__prop_dict = {}
        try:
            self.__is_utf8 = (getpreferredencoding().lower() == 'utf-8')
        except:
            self.__is_utf8 = False
        self.__ibus_version = 0.0

#        self.__lookup_table = ibus.LookupTable.new(page_size=9,
#                                                   cursor_pos=0,
#                                                   cursor_visible=True,
#                                                   round=True)
        size = self.__prefs.get_value('common', 'page_size')
        self.__lookup_table = IBus.LookupTable.new(page_size=size,
                                                   cursor_pos=0,
                                                   cursor_visible=True,
                                                   round=True)
        self.__prop_list = self.__init_props()

        mode = self.__prefs.get_value('common', 'input_mode')
        mode = 'InputMode.' + ['Hiragana', 'Katakana', 'HalfWidthKatakana',
                               'Latin', 'WideLatin'][mode]
        self.__input_mode_activate(mode, IBus.PropState.CHECKED)

        mode = self.__prefs.get_value('common', 'typing_method')
        mode = 'TypingMode.' + ['Romaji', 'Kana', 'ThumbShift'][mode]
        self.__typing_mode_activate(mode, IBus.PropState.CHECKED)

        mode = self.__prefs.get_value('common', 'conversion_segment_mode')
        mode = 'SegmentMode.' + ['Multi', 'Single',
                                 'ImmediateMulti', 'ImmediateSingle'][mode]
        self.__segment_mode_activate(mode, IBus.PropState.CHECKED)

        # use reset to init values
        self.__reset()

    def __get_ibus_version(self):
        if self.__ibus_version == 0.0:
            self.__ibus_version = \
                IBus.MAJOR_VERSION + IBus.MINOR_VERSION / 1000.0 + \
                IBus.MICRO_VERSION / 1000000.0
        return self.__ibus_version

    # reset values of engine
    def __reset(self):
        self.__preedit_ja_string = jastring.JaString(Engine.__typing_mode)
        self.__convert_chars = u''
        self.__cursor_pos = 0
        self.__convert_mode = CONV_MODE_OFF
        self.__segments = list()
        self.__lookup_table.clear()
        self.__lookup_table_visible = False
        self._MM = 0
        self._SS = 0
        self._H = 0
        self._RMM = 0
        self._RSS = 0
        if self.__idle_id != 0:
            GObject.source_remove(self.__idle_id)
            self.__idle_id = 0

    def __init_props(self):
        anthy_props = IBus.PropList()

        # init input mode properties
        input_mode_prop = IBus.Property(key=u'InputMode',
                                        prop_type=IBus.PropType.MENU,
                                        label=IBus.Text.new_from_string(u'あ'),
                                        icon='',
                                        tooltip=IBus.Text.new_from_string(UN(_("Switch input mode"))),
                                        sensitive=True,
                                        visible=True,
                                        state=IBus.PropState.UNCHECKED,
                                        sub_props=None)
        self.__prop_dict[u'InputMode'] = input_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key=u'InputMode.Hiragana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_('Hiragana'))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'InputMode.Katakana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Katakana"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'InputMode.HalfWidthKatakana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Half width katakana"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'InputMode.Latin',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Latin"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'InputMode.WideLatin',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Wide Latin"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))

        props.get(self.__input_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        input_mode_prop.set_sub_props(props)
        anthy_props.append(input_mode_prop)

        # typing input mode properties
        typing_mode_prop = IBus.Property(key=u'TypingMode',
                                         prop_type=IBus.PropType.MENU,
                                         label=IBus.Text.new_from_string(u'R'),
                                         icon='',
                                         tooltip=IBus.Text.new_from_string(UN(_("Switch typing mode"))),
                                         sensitive=True,
                                         visible=True,
                                         state=IBus.PropState.UNCHECKED,
                                         sub_props=None)
        self.__prop_dict[u'TypingMode'] = typing_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key=u'TypingMode.Romaji',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Romaji"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'TypingMode.Kana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Kana"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'TypingMode.ThumbShift',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Thumb shift"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.get(Engine.__typing_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        typing_mode_prop.set_sub_props(props)
        anthy_props.append(typing_mode_prop)

        self.__set_segment_mode_props(anthy_props)
        self.__set_dict_mode_props(anthy_props)
        self.__set_dict_config_props(anthy_props)
        anthy_props.append(IBus.Property(key=u'setup',
                                         label=IBus.Text.new_from_string(UN(_("Preferences - Anthy"))),
                                         icon=u'gtk-preferences',
                                         tooltip=IBus.Text.new_from_string(UN(_("Configure Anthy")))))

        return anthy_props

    def __init_signal(self):
        signal.signal(signal.SIGHUP, self.__signal_cb)
        signal.signal(signal.SIGINT, self.__signal_cb)
        signal.signal(signal.SIGQUIT, self.__signal_cb)
        signal.signal(signal.SIGABRT, self.__signal_cb)
        signal.signal(signal.SIGTERM, self.__signal_cb)

    def __signal_cb(self, signum, object):
        self.__remove_dict_files()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def __set_segment_mode_props(self, anthy_props):
        segment_mode_prop = IBus.Property(key=u'SegmentMode',
                                          prop_type=IBus.PropType.MENU,
                                          label=IBus.Text.new_from_string(u'連'),
                                          icon=None,
                                          tooltip=IBus.Text.new_from_string(UN(_("Switch conversion mode"))),
                                          sensitive=True,
                                          visible=True,
                                          state=IBus.PropState.UNCHECKED,
                                          sub_props=None)
        self.__prop_dict[u'SegmentMode'] = segment_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key=u'SegmentMode.Multi',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Multiple segment"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'SegmentMode.Single',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Single segment"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'SegmentMode.ImmediateMulti',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Immediate conversion (Multiple segment)"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'SegmentMode.ImmediateSingle',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_("Immediate conversion (Single segment)"))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.get(self.__segment_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        segment_mode_prop.set_sub_props(props)
        anthy_props.append(segment_mode_prop)

    def __set_dict_mode_props(self, anthy_props):
        short_label = self.__prefs.get_value('dict/file/embedded',
                                             'short_label')
        dict_mode_prop = IBus.Property(key=u'DictMode',
                                       prop_type=IBus.PropType.MENU,
                                       label=IBus.Text.new_from_string(UN(short_label)),
                                       icon=None,
                                       tooltip=IBus.Text.new_from_string(UN(_("Switch Dictionary"))),
                                       sensitive=True,
                                       visible=True,
                                       state=IBus.PropState.UNCHECKED,
                                       sub_props=None)
        self.__prop_dict[u'DictMode'] = dict_mode_prop
        props = IBus.PropList()

        long_label = self.__prefs.get_value('dict/file/embedded',
                                            'long_label')
        props.append(IBus.Property(key=u'DictMode.embedded',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(UN(_(long_label))),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        for file in self.__prefs.get_value('dict', 'files'):
            self._link_dict_file(file)
            id = self._get_dict_id_from_file(file)
            if id == None:
                continue
            section = 'dict/file/' + id
            if not self.__prefs.get_value(section, 'single'):
                continue
            key = 'DictMode.' + id
            long_label = self.__prefs.get_value(section, 'long_label')
            if 'is_system' in self.__prefs.keys(section) and \
               self.__prefs.get_value(section, 'is_system'):
                uni_long_label = UN(_(long_label))
            else:
                uni_long_label = UN(long_label)
            props.append(IBus.Property(key=UN(key),
                                       prop_type=IBus.PropType.RADIO,
                                       label=IBus.Text.new_from_string(uni_long_label),
                                       icon=None,
                                       tooltip=None,
                                       sensitive=True,
                                       visible=True,
                                       state=IBus.PropState.UNCHECKED,
                                       sub_props=None))

        props.get(self.__dict_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        dict_mode_prop.set_sub_props(props)
        anthy_props.append(dict_mode_prop)
        self.__init_signal()

    def __set_dict_config_props(self, anthy_props):
        admin_command = self.__prefs.get_value('common', 'dict_admin_command')
        icon_path = self.__prefs.get_value('common', 'dict_config_icon')

        if not path.exists(admin_command[0]):
            return
        label = UN(_("Dictionary - Anthy"))
        if icon_path and path.exists(icon_path):
            icon = UN(icon_path)
        else:
            # Translators: "Dic" means 'dictionary', One kanji may be good.
            label = UN(_("Dic"))
            icon = u''

        dict_prop = IBus.Property(key=u'setup-dict-kasumi',
                                  prop_type=IBus.PropType.MENU,
                                  label=IBus.Text.new_from_string(label),
                                  icon=icon,
                                  tooltip=IBus.Text.new_from_string(UN(_("Configure dictionaries"))),
                                  sensitive=True,
                                  visible=True,
                                  state=IBus.PropState.UNCHECKED,
                                  sub_props=None)
        self.__prop_dict[u'setup-dict-kasumi'] = dict_prop

        props = IBus.PropList()
        props.append(IBus.Property(key=u'setup-dict-kasumi-admin',
                                   prop_type=IBus.PropType.NORMAL,
                                   label=IBus.Text.new_from_string(UN(_("Edit dictionaries"))),
                                   icon=icon,
                                   tooltip=IBus.Text.new_from_string(UN(_("Launch the dictionary tool"))),
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key=u'setup-dict-kasumi-word',
                                   prop_type=IBus.PropType.NORMAL,
                                   label=IBus.Text.new_from_string(UN(_("Add words"))),
                                   icon=icon,
                                   tooltip=IBus.Text.new_from_string(UN(_("Add words in the dictionary"))),
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        dict_prop.set_sub_props(props)
        anthy_props.append(dict_prop)

    def __get_clipboard(self, clipboard, text, data):
        clipboard_text = clipboard.wait_for_text ()

        if data == CLIPBOARD_RECONVERT:
            self.__update_reconvert(clipboard_text)

        return clipboard_text

    def __get_single_dict_files(self):
        files = self.__prefs.get_value('dict', 'files')
        single_files = []
        for file in files:
            id = self._get_dict_id_from_file(file)
            if id == None:
                continue
            section = 'dict/file/' + id
            if self.__prefs.get_value(section, 'single'):
                single_files.append(file)
        return single_files

    def __remove_dict_files(self):
        for file in self.__prefs.get_value('dict', 'files'):
            self._remove_dict_file(file)

    def update_preedit(self, string, attrs, cursor_pos, visible):
        text = IBus.Text.new_from_string(string)
        for attr in attrs:
            text.append_attribute(attr['type'],
                                  attr['value'],
                                  attr['start_index'],
                                  attr['end_index'])
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if self.__get_ibus_version() >= 1.003 and mode == 1:
            self.update_preedit_text_with_mode(text,
                                               cursor_pos, visible,
                                               IBus.PreeditFocusMode.COMMIT)
        else:
            self.update_preedit_text(text,
                                     cursor_pos, visible)

    def update_aux_string(self, string, attrs, visible):
        text = IBus.Text.new_from_string(string)
        i = 0
        while attrs.get(i) != None:
            attr = attrs.get(i)
            text.append_attribute(attr.get_attr_type(),
                                  attr.get_value(),
                                  attr.get_start_index(),
                                  attr.get_end_index())
            i += 1
        self.update_auxiliary_text(text, visible)

    def do_page_up(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_up():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = UN(self.__lookup_table.get_candidate(index).get_text())
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def do_page_down(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_down():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = UN(self.__lookup_table.get_candidate(index).get_text())
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def do_cursor_up(self):
        # only process cursor down in convert mode
        # if self.__convert_mode != CONV_MODE_ANTHY:
        if self.__convert_mode != CONV_MODE_ANTHY and self.__convert_mode != CONV_MODE_PREDICTION:
            return False

        if not self.__lookup_table.cursor_up():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = UN(self.__lookup_table.get_candidate(index).get_text())
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def do_cursor_down(self):
        # only process cursor down in convert mode
        # if self.__convert_mode != CONV_MODE_ANTHY:
        if self.__convert_mode != CONV_MODE_ANTHY and self.__convert_mode != CONV_MODE_PREDICTION:
            return False

        if not self.__lookup_table.cursor_down():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = UN(self.__lookup_table.get_candidate(index).get_text())
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def do_candidate_clicked(self, index, button, state):
        if index == 9:
            keyval = IBus.KEY_0
        else:
            keyval = IBus.KEY_1 + index
        self.__on_key_number(keyval)

    def __commit_string(self, text):
        self.__reset()
        self.commit_text(IBus.Text.new_from_string(text))
        self.__invalidate()

    def __shrink_segment(self, relative_size):
        self.__context.resize_segment(self.__cursor_pos, relative_size)
        nr_segments = self.__context.get_nr_segments()
        del self.__segments[self.__cursor_pos:]
        for i in xrange(self.__cursor_pos, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = UN(buf)
            self.__segments.append((0, text))
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def do_process_key_event(self, keyval, keycode, state):
        try:
            return self.__process_key_event_internal2(keyval, keycode, state)
        except:
            import traceback
            traceback.print_exc()
            return False

    def do_property_activate(self, prop_name, state):

        if state == IBus.PropState.CHECKED:
            if prop_name == None:
                return
            elif prop_name.startswith(u'InputMode.'):
                self.__input_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u'TypingMode.'):
                self.__typing_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u'SegmentMode.'):
                self.__segment_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u'DictMode.'):
                self.__dict_mode_activate(prop_name, state)
                return
        else:
            if prop_name == 'setup':
                self.__start_setup()
            elif prop_name == 'setup-dict-kasumi-admin':
                self.__start_dict_admin()
            elif prop_name == 'setup-dict-kasumi-word':
                self.__start_add_word()
            else:
                self.__prop_dict[prop_name].set_state(state)
                if prop_name == 'DictMode':
                    sub_name = self.__dict_mode_get_prop_name(self.__dict_mode)
                    if sub_name == None:
                        return
                    self.__dict_mode_activate(sub_name,
                                              IBus.PropState.CHECKED)

    def __input_mode_activate(self, prop_name, state):
        input_modes = {
            u'InputMode.Hiragana' : (INPUT_MODE_HIRAGANA, u'あ'),
            u'InputMode.Katakana' : (INPUT_MODE_KATAKANA, u'ア'),
            u'InputMode.HalfWidthKatakana' : (INPUT_MODE_HALF_WIDTH_KATAKANA, u'_ｱ'),
            u'InputMode.Latin' : (INPUT_MODE_LATIN, u'_A'),
            u'InputMode.WideLatin' : (INPUT_MODE_WIDE_LATIN, u'Ａ'),
        }

        if prop_name not in input_modes:
            print >> sys.stderr, 'Unknown prop_name = %s' % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        mode, label_text = input_modes[prop_name]
        if self.__input_mode == mode:
            return

        label = IBus.Text.new_from_string(label_text)
        self.__input_mode = mode
        prop = self.__prop_dict[u'InputMode']
        prop.set_label(label)
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __typing_mode_activate(self, prop_name, state):
        typing_modes = {
            u'TypingMode.Romaji' : (jastring.TYPING_MODE_ROMAJI, u'R'),
            u'TypingMode.Kana' : (jastring.TYPING_MODE_KANA, u'か'),
            u'TypingMode.ThumbShift' : (jastring.TYPING_MODE_THUMB_SHIFT, u'親'),
        }

        if prop_name not in typing_modes:
            print >> sys.stderr, 'Unknown prop_name = %s' % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        if prop_name == u'TypingMode.ThumbShift':
            self._reset_thumb()

        mode, label_text = typing_modes[prop_name]

        label = IBus.Text.new_from_string(label_text)
        Engine.__typing_mode = mode
        prop = self.__prop_dict[u'TypingMode']
        prop.set_label(label)
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __refresh_typing_mode_property(self):
        prop = self.__prop_dict[u'TypingMode']
        modes = {
            jastring.TYPING_MODE_ROMAJI : (u'TypingMode.Romaji', u'R'),
            jastring.TYPING_MODE_KANA : (u'TypingMode.Kana', u'か'),
            jastring.TYPING_MODE_THUMB_SHIFT : (u'TypingMode.ThumbShift', u'親'),
        }
        prop_name, label_text = modes.get(Engine.__typing_mode, (None, None))
        if prop_name == None or label_text == None:
            return
        label = IBus.Text.new_from_string(label_text)
        _prop = self.__prop_dict[prop_name]
        _prop.set_state(IBus.PropState.CHECKED)
        self.update_property(_prop)
        prop.set_label(label)
        self.update_property(prop)

    def __segment_mode_activate(self, prop_name, state):
        segment_modes = {
            u'SegmentMode.Multi' : (SEGMENT_DEFAULT, u'連'),
            u'SegmentMode.Single' : (SEGMENT_SINGLE, u'単'),
            u'SegmentMode.ImmediateMulti' : (SEGMENT_IMMEDIATE, u'逐|連'),
            u'SegmentMode.ImmediateSingle' :
                (SEGMENT_IMMEDIATE | SEGMENT_SINGLE, u'逐|単'),
        }

        if prop_name not in segment_modes:
            print >> sys.stderr, 'Unknown prop_name = %s' % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        mode, label_text = segment_modes[prop_name]

        label = IBus.Text.new_from_string(label_text)
        self.__segment_mode = mode
        prop = self.__prop_dict[u'SegmentMode']
        prop.set_label(label)
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __dict_mode_get_prop_name(self, mode):
        if mode == 0:
            id = 'embedded'
        else:
            single_files = self.__get_single_dict_files()
            file = single_files[mode - 1]
            id = self._get_dict_id_from_file(file)
        if id == None:
            return None
        return 'DictMode.' + id

    def __dict_mode_activate(self, prop_name, state):
        if prop_name not in self.__prop_dict.keys():
            # The prop_name is added. Need to restart.
            return
        i = prop_name.find('.')
        if i < 0:
            return
        # The id is already quoted.
        id = prop_name[i + 1:]

        file = None
        single_files = self.__get_single_dict_files()

        if id == 'embedded':
            pass
        elif id == 'anthy_zipcode' or id == 'ibus_symbol' or \
             id == 'ibus_oldchar':
            file = self.__prefs.get_value('dict', id)[0]
        else:
            found = False
            for file in single_files:
                if id == self._get_quoted_id(file):
                    found = True
                    break
            if found == False:
                return

        if id == 'embedded':
            dict_name = 'default'
            self.__dict_mode = 0
        else:
            if file not in single_files:
                print >> sys.stderr, "Index error ", file, single_files
                return
            dict_name = 'ibus__' + id
            self.__dict_mode = single_files.index(file) + 1
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        self.__context.init_personality()
        # dict_name is unicode but the argument is str.
        self.__context.do_set_personality(str(dict_name))

        prop = self.__prop_dict[u'DictMode']
        section = 'dict/file/' + id
        label_text = self.__prefs.get_value(section, 'short_label')
        label = IBus.Text.new_from_string(label_text)
        prop.set_label(label)
        self.update_property(prop)

    def __argb(self, a, r, g, b):
        return ((a & 0xff)<<24) + ((r & 0xff) << 16) + ((g & 0xff) << 8) + (b & 0xff)

    def __rgb(self, r, g, b):
        return self.__argb(255, r, g, b)

    def do_focus_in(self):
        self.register_properties(self.__prop_list)
        self.__refresh_typing_mode_property()
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if mode == 2:
            self.__update_input_chars()
#        self.__reset()
#        self.__invalidate()
        size = self.__prefs.get_value('common', 'page_size')
        if size != self.__lookup_table.get_page_size():
            self.__lookup_table.set_page_size(size)

    def do_focus_out(self):
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if mode == 0 or mode == 1:
            self.__reset()
            self.__invalidate()

    def do_disable(self):
        self.__reset()
        self.__invalidate()

    def do_reset(self):
        self.__reset()
        self.__invalidate()

    def do_destroy(self):
        if self.__idle_id != 0:
            GObject.source_remove(self.__idle_id)
            self.__idle_id = 0
        self.__remove_dict_files()
        # It seems the parent do_destroy and destroy are different.
        # The parent do_destroy calls self destroy infinitely.
        super(Engine,self).destroy()

    def __join_all_segments(self):
        while True:
            nr_segments = self.__context.get_nr_segments()
            seg = nr_segments - self.__cursor_pos

            if seg > 1:
                self.__context.resize_segment(self.__cursor_pos, 1)
            else:
                break

    def __normalize_preedit(self, preedit):
        if not self.__is_utf8:
            return preedit
        for key in romaji_normalize_rule.keys():
            if preedit.find(key) >= 0:
                for value in romaji_normalize_rule[key]:
                    preedit = preedit.replace(key, value)
        return preedit

    # begine convert
    def __begin_anthy_convert(self):
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__end_anthy_convert()
        if self.__convert_mode == CONV_MODE_ANTHY:
            return
        self.__convert_mode = CONV_MODE_ANTHY

#        text, cursor = self.__preedit_ja_string.get_hiragana()
        text, cursor = self.__preedit_ja_string.get_hiragana(True)

        text = self.__normalize_preedit(text)
        self.__context.set_string(text.encode('utf8'))
        if self.__segment_mode & SEGMENT_SINGLE:
            self.__join_all_segments()
        nr_segments = self.__context.get_nr_segments()

        for i in xrange(0, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = UN(buf)
            self.__segments.append((0, text))

        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__cursor_pos = nr_segments - 1
        else:
            self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False

    def __end_anthy_convert(self):
        if self.__convert_mode == CONV_MODE_OFF:
            return

        self.__convert_mode = CONV_MODE_OFF
        self.__convert_chars = u''
        self.__segments = list()
        self.__cursor_pos = 0
        self.__lookup_table.clear()
        self.__lookup_table_visible = False

    def __end_convert(self):
        self.__end_anthy_convert()

    # test case 'verudhi' can show U+3046 + U+309B and U+3094
    def __candidate_cb(self, candidate):
        if not self.__is_utf8:
            return
        for key in romaji_utf8_rule.keys():
            if candidate.find(key) >= 0:
                for value in romaji_utf8_rule[key]:
                    candidate = candidate.replace(key, value)
                    self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))

    def __fill_anthy_zipcode_strip(self, dict_file, id):
        import re
        text = self.__preedit_ja_string.get_latin()[0]
        if text.find('-') < 0:
            return
        text = text.replace('-', '')
        section = 'dict/file/' + id
        if 'encoding' not in self.__prefs.keys(section):
            section = 'dict/file/default'
        encoding = self.__prefs.get_value(section, 'encoding')
        contents = unicode(open(dict_file).read(), encoding)
        expression = re.compile('^' + text + '[ \t]')

        found = False
        dict_dest = None
        for line in contents.split('\n'):
            matched = expression.search(line)
            if matched:
                found = True
                dict_dest = UN(matched.string).split(' ')[2]
                break
        if found:
            self.__lookup_table.append_candidate(IBus.Text.new_from_string(dict_dest))

    def __fill_lookup_table_dict_mode(self):
        if self.__dict_mode <= 0:
            return
        single_files = self.__get_single_dict_files()
        file = single_files[self.__dict_mode - 1]
        if file == None:
            return
        id = self._get_dict_id_from_file(file)
        if id == None:
            return
        if id == 'anthy_zipcode':
            self.__fill_anthy_zipcode_strip(file, id)

    def __fill_lookup_table(self):
        if self.__convert_mode == CONV_MODE_PREDICTION:
            nr_predictions = self.__context.get_nr_predictions()

            # fill lookup_table
            self.__lookup_table.clear()
            for i in xrange(0, seg_stat.nr_predictions):
                buf = self.__context.get_prediction(i)
                candidate = UN(buf)
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))
                self.__candidate_cb(candidate)
            return

        # get segment stat
        nr_candidates = self.__context.get_nr_candidates(self.__cursor_pos)

        # fill lookup_table
        self.__lookup_table.clear()
        for i in xrange(0, nr_candidates):
            buf = self.__context.get_segment(self.__cursor_pos, i)
            candidate = UN(buf)
            self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))
            self.__candidate_cb(candidate)
        self.__fill_lookup_table_dict_mode()


    def __invalidate(self):
        if self.__idle_id != 0:
            return
        self.__idle_id = GObject.idle_add(self.__update,
                                          priority = GObject.PRIORITY_LOW)

#    def __get_preedit(self):
    def __get_preedit(self, commit=False):
        if self.__input_mode == INPUT_MODE_HIRAGANA:
#            text, cursor = self.__preedit_ja_string.get_hiragana()
            text, cursor = self.__preedit_ja_string.get_hiragana(commit)
        elif self.__input_mode == INPUT_MODE_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_katakana()
            text, cursor = self.__preedit_ja_string.get_katakana(commit)
        elif self.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
            text, cursor = self.__preedit_ja_string.get_half_width_katakana(commit)
        else:
            text, cursor = u'', 0
        return text, cursor

    def __update_input_chars(self):
        text, cursor = self.__get_preedit()
        attrs = []
        attrs.append({'type': IBus.AttrType.UNDERLINE,
                      'value': IBus.AttrUnderline.SINGLE,
                      'start_index': 0,
                      'end_index': len(text)})

        self.update_preedit(text,
            attrs, cursor, not self.__preedit_ja_string.is_empty())
        self.update_aux_string(u'', IBus.AttrList(), False)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update_convert_chars(self):
#        if self.__convert_mode == CONV_MODE_ANTHY:
        if self.__convert_mode == CONV_MODE_ANTHY or self.__convert_mode == CONV_MODE_PREDICTION:
            self.__update_anthy_convert_chars()
            return
        if self.__convert_mode == CONV_MODE_HIRAGANA:
#            text, cursor = self.__preedit_ja_string.get_hiragana()
            text, cursor = self.__preedit_ja_string.get_hiragana(True)
        elif self.__convert_mode == CONV_MODE_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_katakana()
            text, cursor = self.__preedit_ja_string.get_katakana(True)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
            text, cursor = self.__preedit_ja_string.get_half_width_katakana(True)
        elif self.__convert_mode == CONV_MODE_LATIN_0:
            text, cursor = self.__preedit_ja_string.get_latin()
            if text == text.lower():
                self.__convert_mode = CONV_MODE_LATIN_1
        elif self.__convert_mode == CONV_MODE_LATIN_1:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.lower()
        elif self.__convert_mode == CONV_MODE_LATIN_2:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.upper()
        elif self.__convert_mode == CONV_MODE_LATIN_3:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.capitalize()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_0:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            if text == text.lower():
                self.__convert_mode = CONV_MODE_WIDE_LATIN_1
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_1:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.lower()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_2:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.upper()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_3:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.capitalize()
        self.__convert_chars = text
        attrs = []
        attrs.append({'type': IBus.AttrType.UNDERLINE,
                      'value': IBus.AttrUnderline.SINGLE,
                      'start_index': 0,
                      'end_index': len(text)})
        attrs.append({'type': IBus.AttrType.BACKGROUND,
                      'value': self.__rgb(200, 200, 240),
                      'start_index': 0,
                      'end_index': len(text)})
        attrs.append({'type': IBus.AttrType.FOREGROUND,
                      'value': self.__rgb(0, 0, 0),
                      'start_index': 0,
                      'end_index': len(text)})
        self.update_preedit(text, attrs, len(text), True)

        self.update_aux_string(u'',
            IBus.AttrList(), self.__lookup_table_visible)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update_anthy_convert_chars(self):
        self.__convert_chars = u''
        pos = 0
        for i, (seg_index, text) in enumerate(self.__segments):
            self.__convert_chars += text
            if i < self.__cursor_pos:
                pos += len(text)
        attrs = []
        attrs.append({'type': IBus.AttrType.UNDERLINE,
                      'value': IBus.AttrUnderline.SINGLE,
                      'start_index': 0,
                      'end_index': len(self.__convert_chars)})
        attrs.append({'type': IBus.AttrType.BACKGROUND,
                      'value': self.__rgb(200, 200, 240),
                      'start_index': pos,
                      'end_index': pos + len(self.__segments[self.__cursor_pos][1])})
        attrs.append({'type': IBus.AttrType.FOREGROUND,
                      'value': self.__rgb(0, 0, 0),
                      'start_index': pos,
                      'end_index': pos + len(self.__segments[self.__cursor_pos][1])})
        self.update_preedit(self.__convert_chars, attrs, pos, True)
        aux_string = u'( %d / %d )' % (self.__lookup_table.get_cursor_pos() + 1, self.__lookup_table.get_number_of_candidates())
        self.update_aux_string(aux_string,
            IBus.AttrList(), self.__lookup_table_visible)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update(self):
        if self.__convert_mode == CONV_MODE_OFF:
            self.__update_input_chars()
        else:
            self.__update_convert_chars()
        self.__idle_id = 0

    def __on_key_return(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
#            text, cursor = self.__get_preedit()
            text, cursor = self.__get_preedit(True)
            self.__commit_string(text)
        elif self.__convert_mode == CONV_MODE_ANTHY:
            for i, (seg_index, text) in enumerate(self.__segments):
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        elif self.__convert_mode == CONV_MODE_PREDICTION:
            self.__context.commit_prediction(self.__segments[0][0])
            self.__commit_string(self.__convert_chars)
        else:
            self.__commit_string(self.__convert_chars)

        return True

    def __on_key_escape(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__reset()
        self.__invalidate()
        return True

    def __on_key_back_space(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode != CONV_MODE_OFF:
            if self.__lookup_table_visible:
                self.__lookup_table.set_cursor_pos(0)
                candidate = UN(self.__lookup_table.get_candidate(0).get_text())
                self.__segments[self.__cursor_pos] = 0, candidate
                self.__lookup_table_visible = False
            elif self.__segments[self.__cursor_pos][0] != \
                    NTH_UNCONVERTED_CANDIDATE:
                buf = self.__context.get_segment(self.__cursor_pos,
                                                 NTH_UNCONVERTED_CANDIDATE)
                self.__segments[self.__cursor_pos] = \
                    NTH_UNCONVERTED_CANDIDATE, UN(buf)
            #elif self._chk_mode('25'):
                '''
                # FIXME: Delete the last char in the active segment.
                #
                # If we are able to delete a char in the active segment,
                # we also should be able to add a char in the active segment.
                # Currently plain preedit, no segment mode, i.e.
                # using self.__preedit_ja_string, can delete or add a char
                # but anthy active segoment mode, i.e.
                # using self.__segments, can not delete or add a char.
                # Deleting a char could be easy here but adding a char is
                # difficult because we need to update both self.__segments
                # and self.__preedit_ja_string but self.__preedit_ja_string
                # has no segment. To convert self.__segments to
                # self.__preedit_ja_string, we may use the reconvert mode
                # but no idea to convert keyvals to hiragana
                # in self__on_key_common() with multiple key typings.

                # Delete a char in the active segment
                all_text = u''
                nr_segments = self.__context.get_nr_segments()
                for i in xrange(0, nr_segments):
                    buf = self.__context.get_segment(i,
                                                     NTH_UNCONVERTED_CANDIDATE)
                    text = UN(buf)
                    if i == self.__cursor_pos and len(text) > 0:
                        text = text[:len(text) - 1]
                    all_text += text

                if all_text == u'':
                    return

                # Set self.__preedit_ja_string by anthy context.
                self.__preedit_ja_string = jastring.JaString(Engine.__typing_mode)
                self.__convert_chars = self.__normalize_preedit(all_text)
                for i in xrange(0, len(self.__convert_chars)):
                    keyval = self.__convert_chars[i]
                    self.__preedit_ja_string.insert(unichr(ord (keyval)))
                self.__context.set_string(self.__convert_chars.encode('utf8'))

                # Set self.__segments by anty context
                # for editable self.__segments,
                # save NTH_UNCONVERTED_CANDIDATE
                nr_segments = self.__context.get_nr_segments()
                if self.__cursor_pos >= nr_segments and \
                   nr_segments > 0:
                    self.__cursor_pos = nr_segments - 1
                for i in xrange(self.__cursor_pos, nr_segments):
                    if i == self.__cursor_pos:
                        index = NTH_UNCONVERTED_CANDIDATE
                    else:
                        index = 0
                    buf = self.__context.get_segment(i,
                                                     index)
                    text = UN(buf)
                    self.__segments[i] = index, text

                # Update self.__lookup_table
                self.__fill_lookup_table()
                '''
            else:
                self.__end_convert()
        else:
            self.__preedit_ja_string.remove_before()

        self.__invalidate()
        return True

    def __on_key_delete(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode != CONV_MODE_OFF:
            self.__end_convert()
        else:
            self.__preedit_ja_string.remove_after()

        self.__invalidate()
        return True

    '''def __on_key_hiragana_katakana(self):
        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        if self.__input_mode >= INPUT_MODE_HIRAGANA and \
           self.__input_mode < INPUT_MODE_HALF_WIDTH_KATAKANA:
            self.__input_mode += 1
        else:
            self.__input_mode = INPUT_MODE_HIRAGANA

        modes = { INPUT_MODE_HIRAGANA: u'あ',
                  INPUT_MODE_KATAKANA: u'ア',
                  INPUT_MODE_HALF_WIDTH_KATAKANA: u'_ｱ' }

        prop = self.__prop_dict[u'InputMode']
        label_text = modes[self.__input_mode]
        label = IBus.Text.new_from_string(label_text)
        prop.set_label(label)
        self.update_property(prop)

        self.__invalidate()
        return True'''

    '''def __on_key_muhenka(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        new_mode = CONV_MODE_HIRAGANA
        if self.__convert_mode < CONV_MODE_WIDE_LATIN_3 and \
           self.__convert_mode >= CONV_MODE_HIRAGANA :
            self.__convert_mode += 1
        else:
            self.__convert_mode = CONV_MODE_HIRAGANA

        self.__invalidate()

        return True'''

    '''def __on_key_henkan(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__convert_mode != CONV_MODE_ANTHY:
            self.__begin_anthy_convert()
            self.__invalidate()
        elif self.__convert_mode == CONV_MODE_ANTHY:
            self.__lookup_table_visible = True
            self.do_cursor_down()
        return True'''

    '''def __on_key_space(self, wide=False):
        if self.__input_mode == INPUT_MODE_WIDE_LATIN or wide:
            # Input Wide space U+3000
            wide_char = symbol_rule[unichr(IBus.KEY_space)]
            self.__commit_string(wide_char)
            return True

        if self.__preedit_ja_string.is_empty():
            if self.__input_mode in (INPUT_MODE_HIRAGANA, INPUT_MODE_KATAKANA):
                # Input Wide space U+3000
                wide_char = symbol_rule[unichr(IBus.KEY_space)]
                self.__commit_string(wide_char)
                return True
            else:
                # Input Half space U+0020
                self.__commit_string(unichr(IBus.KEY_space))
                return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            self.__begin_anthy_convert()
            self.__invalidate()
        elif self.__convert_mode == CONV_MODE_ANTHY:
            self.__lookup_table_visible = True
            self.do_cursor_down()
        return True'''

    def __on_key_up(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__lookup_table_visible = True
        self.do_cursor_up()
        return True

    def __on_key_down(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__lookup_table_visible = True
        self.do_cursor_down()
        return True

    def __on_key_page_up(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__lookup_table_visible == True:
            self.do_page_up()
        return True

    def __on_key_page_down(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__lookup_table_visible == True:
            self.do_page_down()
        return True

    '''def __on_key_left(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(-1)
            self.__invalidate()
            return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            return True

        if self.__cursor_pos == 0:
            return True
        self.__cursor_pos -= 1
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True'''

    def __on_key_right(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(1)
            self.__invalidate()
            return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            return True

        if self.__cursor_pos + 1 >= len(self.__segments):
            return True

        self.__cursor_pos += 1
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def __on_key_number(self, keyval):
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False
        if not self.__lookup_table_visible:
            return False

        if keyval == IBus.KEY_0:
            keyval = IBus.KEY_9 + 1
        index = keyval - IBus.KEY_1

        return self.__on_candidate_index_in_page(index)

    def __on_key_conv(self, mode):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        if mode == 0 or mode == 1:
            if self.__convert_mode == CONV_MODE_HIRAGANA + mode:
                return True
            self.__convert_mode = CONV_MODE_HIRAGANA + mode
        elif mode == 2:
            if self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
                return True
            self.__convert_mode = CONV_MODE_HALF_WIDTH_KATAKANA
        elif mode == 3:
            if CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
                self.__convert_mode += 1
                if self.__convert_mode > CONV_MODE_WIDE_LATIN_3:
                    self.__convert_mode = CONV_MODE_WIDE_LATIN_1
            else:
                self.__convert_mode = CONV_MODE_WIDE_LATIN_0
        elif mode == 4:
            if CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
                self.__convert_mode += 1
                if self.__convert_mode > CONV_MODE_LATIN_3:
                    self.__convert_mode = CONV_MODE_LATIN_1
            else:
                self.__convert_mode = CONV_MODE_LATIN_0
        else:
            print >> sys.stderr, 'Unkown convert mode (%d)!' % mode
            return False
        self.__invalidate()
        return True

    def __on_key_common(self, keyval, state=0):

        if self.__input_mode == INPUT_MODE_LATIN:
            # Input Latin chars
            char = unichr(keyval)
            self.__commit_string(char)
            return True

        elif self.__input_mode == INPUT_MODE_WIDE_LATIN:
            #  Input Wide Latin chars
            char = unichr(keyval)
            wide_char = None#symbol_rule.get(char, None)
            if wide_char == None:
                wide_char = unichar_half_to_full(char)
            self.__commit_string(wide_char)
            return True

        # Input Japanese
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            # Commit nothing
            pass
        elif self.__convert_mode == CONV_MODE_ANTHY:
            for i, (seg_index, text) in enumerate(self.__segments):
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        elif self.__convert_mode != CONV_MODE_OFF:
            self.__commit_string(self.__convert_chars)

        # 'n' + '\'' == 'nn' in romaji
        if (keyval >= ord('A') and keyval <= ord('Z')) or \
           (keyval >= ord('a') and keyval <= ord('z')):
            shift = (state & IBus.ModifierType.SHIFT_MASK) != 0
        else:
            shift = False
        self.__preedit_ja_string.set_shift(shift)
        self.__preedit_ja_string.insert(unichr(keyval))
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__begin_anthy_convert()
        self.__invalidate()
        return True

#=======================================================================
    @classmethod
    def CONFIG_RELOADED(cls, bus):
        print 'RELOADED'
        if not cls.__prefs:
            cls.__prefs = AnthyPrefs(bus)

        cls.__keybind = cls._mk_keybind()

        jastring.JaString._prefs = cls.__prefs

    @classmethod
    def CONFIG_VALUE_CHANGED(cls, bus, section, name, variant):
        print 'VALUE_CHAMGED =', section, name, variant

        if not section.startswith('engine/anthy'):
            # This value is used for IBus.config.set_value only.
            return

        # The key was deleted by dconf.
        # test case: update /desktop/ibus/engine/anthy/thumb/ls
        # and reset the key with dconf direclty.
        if variant.get_type_string() == '()':
            cls.__prefs.undo_item(section, name)
            return

        value = cls.__prefs.variant_to_value(variant)
        base_sec = section[len(cls.__prefs._prefix) + 1:]
        sec = cls._get_shortcut_type()
        if base_sec == sec:
            cmd = '_Engine__cmd_' + name
            old = cls.__prefs.get_value(sec, name)
            value = value if value != [''] else []
            for s in set(old).difference(value):
                cls.__keybind.get(cls._s_to_key(s), []).remove(cmd)

            keys = cls.__prefs.keys(sec)
            for s in set(value).difference(old):
                cls.__keybind.setdefault(cls._s_to_key(s), []).append(cmd)
                cls.__keybind.get(cls._s_to_key(s)).sort(
                    lambda a, b: cmp(keys.index(a[13:]), keys.index(b[13:])))

            cls.__prefs.set_value(sec, name, value)
        elif base_sec == 'common':
            cls.__prefs.set_value(base_sec, name, value)
            if name == 'shortcut_type':
                cls.__keybind = cls._mk_keybind()
        elif base_sec == 'thumb':
            cls.__prefs.set_value(base_sec, name, value)
            cls._reset_thumb()
        elif base_sec == 'dict':
            cls._set_dict_files_value(base_sec, name, value)
        elif base_sec.startswith('dict/file/'):
            if base_sec not in cls.__prefs.sections():
                cls._fetch_dict_values(base_sec)
            cls.__prefs.set_value(base_sec, name, value)
        elif base_sec:
            cls.__prefs.set_value(base_sec, name, value)
        else:
            cls.__prefs.set_value(section, name, value)

    @classmethod
    def _mk_keybind(cls):
        keybind = {}
        sec = cls._get_shortcut_type()
        for k in cls.__prefs.keys(sec):
            cmd = '_Engine__cmd_' + k
            for s in cls.__prefs.get_value(sec, k):
                keybind.setdefault(cls._s_to_key(s), []).append(cmd)
        return keybind

    @classmethod
    def _get_shortcut_type(cls):
        try:
            t = 'shortcut/' + cls.__prefs.get_value('common', 'shortcut_type')
        except:
            t = 'shortcut/default'
        return t

    @classmethod
    def _s_to_key(cls, s):
        keyval = IBus.keyval_from_name(s.split('+')[-1])
        s = s.lower()
        state = ('shift+' in s and IBus.ModifierType.SHIFT_MASK or 0) | (
                 'ctrl+' in s and IBus.ModifierType.CONTROL_MASK or 0) | (
                 'alt+' in s and IBus.ModifierType.MOD1_MASK or 0)
        return cls._mk_key(keyval, state)

    @classmethod
    def _reset_thumb(cls):
        if cls.__thumb == None:
            import thumb
            cls.__thumb = thumb.ThumbShiftKeyboard(cls.__prefs)

        else:
            cls.__thumb.reset()

    @classmethod
    def _get_userhome(cls):
        if 'HOME' not in environ:
            import pwd
            userhome = pwd.getpwuid(os.getuid()).pw_dir
        else:
            userhome = environ['HOME']
        userhome = userhome.rstrip('/')
        return userhome

    @classmethod
    def _get_quoted_id(cls, file):
        id = file
        has_mbcs = False

        for i in xrange(0, len(id)):
            if ord(id[i]) >= 0x7f:
                    has_mbcs = True
                    break
        if has_mbcs:
            id = id.encode('hex')

        if id.find('/') >=0:
            id = id[id.rindex('/') + 1:]
        if id.find('.') >=0:
            id = id[:id.rindex('.')]

        if id.startswith('0x'):
            id = id.encode('hex')
            has_mbcs = True
        if has_mbcs:
            id = '0x' + id
        return id

    @classmethod
    def _get_dict_id_from_file(cls, file):
        if file in cls.__prefs.get_value('dict', 'anthy_zipcode'):
            id = 'anthy_zipcode'
        elif file in cls.__prefs.get_value('dict', 'ibus_symbol'):
            id = 'ibus_symbol'
        elif file in cls.__prefs.get_value('dict', 'ibus_oldchar'):
            id = 'ibus_oldchar'
        else:
            id = cls._get_quoted_id(file)
        return id

    @classmethod
    def _link_dict_file_with_id(cls, file, id, link_mode):
        if not path.exists(file):
            print >> sys.stderr, file + ' does not exist'
            return
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = cls._get_userhome() + '/.anthy/' + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = cls._get_userhome() + '/.anthy'
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                print >> sys.stderr, directory + ' is not a directory'
                return
        else:
            os.makedirs(directory, 0700)
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            if path.islink(directory + '/' + name):
                print >> sys.stderr, 'Removing ' + name
                os.unlink(directory + '/' + name)
            else:
                alternate = name + str(os.getpid())
                print >> sys.stderr, 'Moving ' + name + ' to ' + alternate
                os.rename(name, alternate)
        os.symlink(file, directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    @classmethod
    def _remove_dict_file_with_id(cls, file, id, link_mode):
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = cls._get_userhome() + '/.anthy/' + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = cls._get_userhome() + '/.anthy'
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                print >> sys.stderr, directory + ' is not a directory'
                return
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            os.unlink(directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    @classmethod
    def _link_dict_file(cls, file):
        id = cls._get_dict_id_from_file(file)
        if id == None:
            return
        section = 'dict/file/' + id
        if section not in cls.__prefs.sections():
            cls._fetch_dict_values(section)
        if cls.__prefs.get_value(section, 'embed'):
            cls._link_dict_file_with_id(file, id, LINK_DICT_EMBEDDED)
        if cls.__prefs.get_value(section, 'single'):
            cls._link_dict_file_with_id(file, id, LINK_DICT_SINGLE)

    @classmethod
    def _remove_dict_file(cls, file):
        id = cls._get_dict_id_from_file(file)
        if id == None:
            return
        section = 'dict/file/' + id
        if section not in cls.__prefs.sections():
            cls._fetch_dict_values(section)
        if cls.__prefs.get_value(section, 'embed'):
            cls._remove_dict_file_with_id(file, id, LINK_DICT_EMBEDDED)
        if cls.__prefs.get_value(section, 'single'):
            cls._remove_dict_file_with_id(file, id, LINK_DICT_SINGLE)

    @classmethod
    def _set_dict_files_value(cls, base_sec, name, value):
        if name == 'files':
            str_list = []
            for file in value:
                str_list.append(cls.__prefs.str(file))
            old_files = cls.__prefs.get_value(base_sec, name)
            for file in old_files:
                if file in str_list:
                    continue
                cls._remove_dict_file(file)
            for file in str_list:
                if file in old_files:
                    continue
                cls._link_dict_file(file)
            cls.__prefs.set_value(base_sec, name, str_list)
        else:
            cls.__prefs.set_value(base_sec, name, value)

    @classmethod
    def _fetch_dict_values(cls, section):
        cls.__prefs.set_new_section(section)
        cls.__prefs.set_new_key(section, 'short_label')
        cls.__prefs.fetch_item(section, 'short_label')
        cls.__prefs.set_value(section, 'short_label',
                              str(cls.__prefs.get_value(section, 'short_label')))
        cls.__prefs.set_new_key(section, 'long_label')
        cls.__prefs.fetch_item(section, 'long_label')
        cls.__prefs.set_value(section, 'long_label',
                              str(cls.__prefs.get_value(section, 'long_label')))
        cls.__prefs.set_new_key(section, 'embed')
        cls.__prefs.fetch_item(section, 'embed')
        cls.__prefs.set_new_key(section, 'single')
        cls.__prefs.fetch_item(section, 'single')
        cls.__prefs.set_new_key(section, 'reverse')
        cls.__prefs.fetch_item(section, 'reverse')

    @staticmethod
    def _mk_key(keyval, state):
        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
            if unichr(keyval) in u'!"#$%^\'()*+,-./:;<=>?@[\]^_`{|}~':
                state |= IBus.ModifierType.SHIFT_MASK
            elif IBus.KEY_a <= keyval <= IBus.KEY_z:
                keyval -= (IBus.KEY_a - IBus.KEY_A)

        return repr([int(state), int(keyval)])

    def process_key_event_thumb(self, keyval, keycode, state):
        if self.__thumb == None:
            self._reset_thumb()

        def on_timeout(keyval):
            if self._MM:
                insert(self.__thumb.get_char(self._MM)[self._SS])
            else:
                cmd_exec([0, RS(), LS()][self._SS])
            self._H = None

        def start(t):
            self._H = GObject.timeout_add(t, on_timeout, keyval)

        def stop():
            if self._H:
                GObject.source_remove(self._H)
                self._H = None
                return True
            return False

        def insert(keyval):
            try:
                self._MM = self._SS = 0
                ret = self.__on_key_common(ord(keyval))
                if (keyval in u',.、。' and
                    self.__prefs.get_value('common', 'behavior_on_period')):
                    return self.__cmd_convert(keyval, state)
                return ret
            except:
                pass

        def cmd_exec(keyval, state=0):
            key = self._mk_key(keyval, state)
            for cmd in self.__keybind.get(key, []):
                print 'cmd =', cmd
                try:
                    if getattr(self, cmd)(keyval, state):
                        return True
                except:
                    print >> sys.stderr, 'Unknown command = %s' % cmd
            return False

        def RS():
            return self.__thumb.get_rs()

        def LS():
            return self.__thumb.get_ls()

        def T1():
            return self.__thumb.get_t1()

        def T2():
            return self.__thumb.get_t2()

        state = state & (IBus.ModifierType.SHIFT_MASK |
                         IBus.ModifierType.CONTROL_MASK |
                         IBus.ModifierType.MOD1_MASK |
                         IBus.ModifierType.RELEASE_MASK)

        if keyval in KP_Table and self.__prefs.get_value('common',
                                                         'ten_key_mode'):
            keyval = KP_Table[keyval]

        if state & IBus.ModifierType.RELEASE_MASK:
            if keyval == self._MM:
                if stop():
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                self._MM = 0
            elif (1 if keyval == RS() else 2) == self._SS:
                if stop():
                    cmd_exec([0, RS(), LS()][self._SS])
                self._SS = 0
            if keyval in [RS(), LS()]:
                self._RSS = 0
            elif keyval == self._RMM:
                self._RMM = 0
        else:
            if keyval in [LS(), RS()] and state == 0:
                if self._SS:
                    stop()
                    cmd_exec([0, RS(), LS()][self._SS])
                    self._SS = 1 if keyval == RS() else 2
                    start(T1())
                elif self._MM:
                    stop()
                    self._RMM = self._MM
                    self._RSS = 1 if keyval == RS() else 2
                    insert(self.__thumb.get_char(self._MM)[1 if keyval == RS() else 2])
                else:
                    if self._RSS == (1 if keyval == RS() else 2):
                        if self._RMM:
                            insert(self.__thumb.get_char(self._RMM)[self._RSS])
                    else:
                        self._SS = 1 if keyval == RS() else 2
                        start(T1())
            elif keyval in self.__thumb.get_chars() and state == 0:
                if self._MM:
                    stop()
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                    start(T2())
                    self._MM = keyval
                elif self._SS:
                    stop()
                    self._RMM = keyval
                    self._RSS = self._SS
                    insert(self.__thumb.get_char(keyval)[self._SS])
                else:
                    if self._RMM  == keyval:
                        if self._RSS:
                            insert(self.__thumb.get_char(self._RMM)[self._RSS])
                    else:
                        if cmd_exec(keyval, state):
                            return True
                        start(T2())
                        self._MM = keyval
            else:
                if self._MM:
                    stop()
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                elif self._SS:
                    stop()
                    cmd_exec([0, RS(), LS()][self._SS])
                if cmd_exec(keyval, state):
                    return True
                elif 0x21 <= keyval <= 0x7e and state & \
                        (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) == 0:
                    if state & IBus.ModifierType.SHIFT_MASK:
                        insert(self.__thumb.get_shift_char(keyval, unichr(keyval)))
                    elif self._SS == 0:
                        insert(unichr(keyval))
                else:
                    if not self.__preedit_ja_string.is_empty():
                        return True
                    return False
        return True

    def __process_key_event_internal2(self, keyval, keycode, state):
        if self.__typing_mode == jastring.TYPING_MODE_THUMB_SHIFT and \
           self.__input_mode not in [INPUT_MODE_LATIN, INPUT_MODE_WIDE_LATIN]:
            return self.process_key_event_thumb(keyval, keycode, state)

        is_press = (state & IBus.ModifierType.RELEASE_MASK) == 0

        state = state & (IBus.ModifierType.SHIFT_MASK |
                         IBus.ModifierType.CONTROL_MASK |
                         IBus.ModifierType.MOD1_MASK)

        # ignore key release events
        if not is_press:
            return False

        if keyval in KP_Table and self.__prefs.get_value('common',
                                                         'ten_key_mode'):
            keyval = KP_Table[keyval]

        key = self._mk_key(keyval, state)
        for cmd in self.__keybind.get(key, []):
            print 'cmd =', cmd
            try:
                if getattr(self, cmd)(keyval, state):
                    return True
            except:
                print >> sys.stderr, 'Unknown command = %s' % cmd

        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
            return False

        if (IBus.KEY_exclam <= keyval <= IBus.KEY_asciitilde or
            keyval == IBus.KEY_yen):
            if self.__typing_mode == jastring.TYPING_MODE_KANA:
                if keyval == IBus.KEY_0 and state == IBus.ModifierType.SHIFT_MASK:
                    keyval = IBus.KEY_asciitilde
                elif keyval == IBus.KEY_backslash and keycode in [132-8, 133-8]:
                    keyval = IBus.KEY_yen
            ret = self.__on_key_common(keyval, state)
            if (unichr(keyval) in u',.' and
                self.__prefs.get_value('common', 'behavior_on_period')):
                return self.__cmd_convert(keyval, state)
            return ret
        else:
            if not self.__preedit_ja_string.is_empty():
                return True
            return False

    def _chk_mode(self, mode):
        if '0' in mode and self.__preedit_ja_string.is_empty():
            return True

        if self.__convert_mode == CONV_MODE_OFF:
            if '1' in mode and not self.__preedit_ja_string.is_empty():
                return True
        elif self.__convert_mode == CONV_MODE_ANTHY:
            if '2' in mode and not self.__lookup_table_visible:
                return True
        elif self.__convert_mode == CONV_MODE_PREDICTION:
            if '3' in mode and not self.__lookup_table_visible:
                return True
        else:
            if '4' in mode:
                return True

        if '5' in mode and self.__lookup_table_visible:
            return True

        return False

    #mod_keys
    def __set_input_mode(self, mode):
        if not self._chk_mode('0'):
            return False

        self.__input_mode_activate(mode, IBus.PropState.CHECKED)

        return True

    def __cmd_on_off(self, keyval, state):
        if self.__input_mode == INPUT_MODE_LATIN:
            return self.__set_input_mode(u'InputMode.Hiragana')
        else:
            return self.__set_input_mode(u'InputMode.Latin')

    def __cmd_circle_input_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: u'InputMode.Katakana',
            INPUT_MODE_KATAKANA: u'InputMode.HalfWidthKatakana',
            INPUT_MODE_HALF_WIDTH_KATAKANA: u'InputMode.Latin',
            INPUT_MODE_LATIN: u'InputMode.WideLatin',
            INPUT_MODE_WIDE_LATIN: u'InputMode.Hiragana'
        }
        return self.__set_input_mode(modes[self.__input_mode])

    def __cmd_circle_kana_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: u'InputMode.Katakana',
            INPUT_MODE_KATAKANA: u'InputMode.HalfWidthKatakana',
            INPUT_MODE_HALF_WIDTH_KATAKANA: u'InputMode.Hiragana',
            INPUT_MODE_LATIN: u'InputMode.Hiragana',
            INPUT_MODE_WIDE_LATIN: u'InputMode.Hiragana'
        }
        return self.__set_input_mode(modes[self.__input_mode])

    def __cmd_latin_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Latin')

    def __cmd_wide_latin_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.WideLatin')

    def __cmd_hiragana_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Hiragana')

    def __cmd_katakana_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Katakana')

    def __cmd_half_katakana(self, keyval, state):
        return self.__set_input_mode(u'InputMode.HalfWidthKatakana')

#    def __cmd_cancel_pseudo_ascii_mode_key(self, keyval, state):
#        pass

    def __cmd_circle_typing_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        modes = {
            jastring.TYPING_MODE_THUMB_SHIFT: u'TypingMode.Romaji',
            jastring.TYPING_MODE_KANA: u'TypingMode.ThumbShift',
            jastring.TYPING_MODE_ROMAJI: u'TypingMode.Kana',
        }
        self.__typing_mode_activate(modes[self.__typing_mode],
                                    IBus.PropState.CHECKED)
        return True

    def __cmd_circle_dict_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        single_files = self.__get_single_dict_files()
        new_mode = self.__dict_mode + 1
        if new_mode > len(single_files):
            new_mode = 0
        self.__dict_mode = new_mode
        prop_name = self.__dict_mode_get_prop_name(self.__dict_mode)
        if prop_name == None:
            return False
        self.__dict_mode_activate(prop_name,
                                  IBus.PropState.CHECKED)
        return True

    #edit_keys
    def __cmd_insert_space(self, keyval, state):
        if (self.__prefs.get_value('common', 'half_width_space') or
            self.__input_mode in [INPUT_MODE_LATIN,
                                  INPUT_MODE_HALF_WIDTH_KATAKANA]):
            return self.__cmd_insert_half_space(keyval, state)
        else:
            return self.__cmd_insert_wide_space(keyval, state)

    def __cmd_insert_alternate_space(self, keyval, state):
        if (self.__prefs.get_value('common', 'half_width_space') or
            self.__input_mode in [INPUT_MODE_LATIN,
                                  INPUT_MODE_HALF_WIDTH_KATAKANA]):
            return self.__cmd_insert_wide_space(keyval, state)
        else:
            return self.__cmd_insert_half_space(keyval, state)

    def __cmd_insert_half_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        self.__commit_string(unichr(IBus.KEY_space))
        return True

    def __cmd_insert_wide_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        char = unichr(IBus.KEY_space)
        wide_char = symbol_rule.get(char, None)
        if wide_char == None:
            wide_char = unichar_half_to_full(char)
        self.__commit_string(wide_char)
        return True

    def __cmd_backspace(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_back_space()

    def __cmd_delete(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_delete()

    def __cmd_commit(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_return()

    def __cmd_convert(self, keyval, state):
        if not self._chk_mode('14'):
            return False

        self.__begin_anthy_convert()
        self.__invalidate()

        return True

    def __cmd_predict(self, keyval, state):
        if not self._chk_mode('14'):
            return False

        text, cursor = self.__preedit_ja_string.get_hiragana(True)

        self.__context.set_prediction_string(text.encode('utf8'))
        nr_predictions = self.__context.get_nr_predictions()

#        for i in range(nr_predictions):
#            print self.__context.get_prediction(i)

        buf = self.__context.get_prediction(0)
        if not buf:
            return False

        text = UN(buf)
        self.__segments.append((0, text))

        self.__convert_mode = CONV_MODE_PREDICTION
        self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False
        self.__invalidate()

        return True

    def __cmd_cancel(self, keyval, state):
        return self.__cmd_cancel_all(keyval, state)

    def __cmd_cancel_all(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            return self.__on_key_escape()
        else:
            self.__end_convert()
            self.__invalidate()
            return True

    def __cmd_reconvert(self, keyval, state):
        if not self.__preedit_ja_string.is_empty():
            # if user has inputed some chars
            return False

        # Use Gtk.Clipboard.request_text() instead of
        # Gtk.Clipboard.wait_for_text() because DBus is timed out.
        clipboard = clipboard_get ('PRIMARY')
        if clipboard:
            clipboard.request_text (self.__get_clipboard, CLIPBOARD_RECONVERT)

        return True

    def __update_reconvert(self, clipboard_text):
        if clipboard_text == None:
            return False

        self.__convert_chars = UN(clipboard_text)
        for i in xrange(0, len(self.__convert_chars)):
            keyval = self.__convert_chars[i]
            self.__preedit_ja_string.insert(unichr(ord (keyval)))

        self.__context.set_string(self.__convert_chars.encode('utf-8'))
        nr_segments = self.__context.get_nr_segments()

        for i in xrange(0, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = UN(buf)
            self.__segments.append((0, text))

        self.__convert_mode = CONV_MODE_ANTHY
        self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False
        self.__invalidate()

        return True

#    def __cmd_do_nothing(self, keyval, state):
#        return True

    #caret_keys
    def __move_caret(self, i):
        if not self._chk_mode('1'):
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(
                -len(self.__preedit_ja_string.get_latin()[0]) if i == 0 else
                i if i in [-1, 1] else
                len(self.__preedit_ja_string.get_latin()[0]))
            self.__invalidate()
            return True

        return False

    def __cmd_move_caret_first(self, keyval, state):
        return self.__move_caret(0)

    def __cmd_move_caret_last(self, keyval, state):
        return self.__move_caret(2)

    def __cmd_move_caret_forward(self, keyval, state):
        return self.__move_caret(1)

    def __cmd_move_caret_backward(self, keyval, state):
        return self.__move_caret(-1)

    #segments_keys
    def __select_segment(self, i):
        if not self._chk_mode('25'):
            return False

        pos = 0 if i == 0 else \
              self.__cursor_pos + i if i in [-1, 1] else \
              len(self.__segments) - 1

        if 0 <= pos < len(self.__segments) and pos != self.__cursor_pos:
            self.__cursor_pos = pos
            self.__lookup_table_visible = False
            self.__fill_lookup_table()
            self.__invalidate()

        return True

    def __cmd_select_first_segment(self, keyval, state):
        return self.__select_segment(0)

    def __cmd_select_last_segment(self, keyval, state):
        return self.__select_segment(2)

    def __cmd_select_next_segment(self, keyval, state):
        return self.__select_segment(1)

    def __cmd_select_prev_segment(self, keyval, state):
        return self.__select_segment(-1)

    def __cmd_shrink_segment(self, keyval, state):
        if not self._chk_mode('25'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__shrink_segment(-1)
            return True

    def __cmd_expand_segment(self, keyval, state):
        if not self._chk_mode('25'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__shrink_segment(1)
            return True

    def __move_cursor_char_length(self, length):
        if self.__input_mode == INPUT_MODE_HIRAGANA:
            self.__preedit_ja_string.move_cursor_hiragana_length(length)
        elif self.__input_mode == INPUT_MODE_KATAKANA:
            self.__preedit_ja_string.move_cursor_katakana_length(length)
        elif self.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
            self.__preedit_ja_string.move_cursor_half_with_katakana_length(length)
        else:
            self.__preedit_ja_string.move_cursor(length)

    def __commit_nth_segment(self, commit_index, keyval, state):

        if commit_index >= len(self.__segments):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            for i in xrange(0, commit_index + 1):
                (seg_index, text) = self.__segments[i]
                self.commit_text(IBus.Text.new_from_string(text))

            text, cursor = self.__get_preedit()
            commit_length = 0
            for i in xrange(0, commit_index + 1):
                buf = self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE)
                commit_length += len(UN(buf))
            self.__move_cursor_char_length(commit_length - cursor)
            for i in xrange(0, commit_length):
                self.__preedit_ja_string.remove_before()
            self.__move_cursor_char_length(cursor - commit_length)

            del self.__segments[0:commit_index + 1]

        if len(self.__segments) == 0:
            self.__reset()
        else:
            if self.__cursor_pos > commit_index:
                self.__cursor_pos -= (commit_index + 1)
            else:
                self.__cursor_pos = 0
            text, cursor = self.__get_preedit()
            self.__convert_chars = text
            self.__context.set_string(text.encode ('utf-8'))

        self.__lookup_table.clear()
        self.__lookup_table.show_cursor (False)
        self.__lookup_table_visible = False
        self.update_aux_string(u'', IBus.AttrList(),
            self.__lookup_table_visible)
        self.__fill_lookup_table()
        self.__invalidate()
        self.__update_input_chars()

        return True

    def __cmd_commit_first_segment(self, keyval, state):
        return self.__commit_nth_segment(0, keyval, state)

    def __cmd_commit_selected_segment(self, keyval, state):
        return self.__commit_nth_segment(self.__cursor_pos, keyval, state)

    #candidates_keys
    def __on_candidate_index_in_page(self, index):
        if not self._chk_mode('5'):
            return False

        if index >= self.__lookup_table.get_page_size():
            return False
        cursor_pos = self.__lookup_table.get_cursor_pos()
        cursor_in_page = self.__lookup_table.get_cursor_in_page()
        real_index = cursor_pos - cursor_in_page + index
        if real_index >= self.__lookup_table.get_number_of_candidates():
            return False
        self.__lookup_table.set_cursor_pos(real_index)
        index = self.__lookup_table.get_cursor_pos()
        candidate = UN(self.__lookup_table.get_candidate(index).get_text())
        self.__segments[self.__cursor_pos] = index, candidate
        self.__lookup_table_visible = False
        self.__on_key_right()
        self.__invalidate()
        return True

    def __cmd_select_first_candidate(self, keyval, state):
        return self.__on_candidate_index_in_page(0)

    def __cmd_select_last_candidate(self, keyval, state):
        return self.__on_candidate_index_in_page(
            self.__lookup_table.get_page_size() - 1)

    def __cmd_select_next_candidate(self, keyval, state):
        if not self._chk_mode('235'):
            return False

        return self.__on_key_down()

    def __cmd_select_prev_candidate(self, keyval, state):
        if not self._chk_mode('235'):
            return False

        return self.__on_key_up()

    def __cmd_candidates_page_up(self, keyval, state):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_page_up()

    def __cmd_candidates_page_down(self, keyval, state):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_page_down()

    #direct_select_keys
    def __select_keyval(self, keyval):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_number(keyval)

    def __cmd_select_candidates_1(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_2(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_3(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_4(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_5(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_6(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_7(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_8(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_9(self, keyval, state):
        return self.__select_keyval(keyval)

    def __cmd_select_candidates_0(self, keyval, state):
        return self.__select_keyval(keyval)

    #convert_keys
    def __cmd_convert_to_char_type_forward(self, keyval, state):
        if self.__convert_mode == CONV_MODE_ANTHY:
            n = self.__segments[self.__cursor_pos][0]
            if n == NTH_HIRAGANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)
            elif n == NTH_KATAKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)
            elif n == NTH_HALFKANA_CANDIDATE:
                return self.__convert_segment_to_latin(-100)
            elif n == -100:
                return self.__convert_segment_to_latin(-101)
            else:
                return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)

        if self.__convert_mode == CONV_MODE_KATAKANA:
            return self.__cmd_convert_to_half_katakana(keyval, state)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
            return self.__cmd_convert_to_latin(keyval, state)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__cmd_convert_to_wide_latin(keyval, state)
        elif (CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode
                                     <= CONV_MODE_WIDE_LATIN_3):
            return self.__cmd_convert_to_hiragana(keyval, state)
        else:
            return self.__cmd_convert_to_katakana(keyval, state)

    def __cmd_convert_to_char_type_backward(self, keyval, state):
        if self.__convert_mode == CONV_MODE_ANTHY:
            n = self.__segments[self.__cursor_pos][0]
            if n == NTH_KATAKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)
            elif n == NTH_HALFKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)
            elif n == -100:
                return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)
            elif n == -101:
                return self.__convert_segment_to_latin(-100)
            else:
                return self.__convert_segment_to_latin(-101)

        if self.__convert_mode == CONV_MODE_KATAKANA:
            return self.__cmd_convert_to_hiragana(keyval, state)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
            return self.__cmd_convert_to_katakana(keyval, state)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__cmd_convert_to_half_katakana(keyval, state)
        elif (CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode
                                     <= CONV_MODE_WIDE_LATIN_3):
            return self.__cmd_convert_to_latin(keyval, state)
        else:
            return self.__cmd_convert_to_wide_latin(keyval, state)

    def __convert_segment_to_kana(self, n):
        if self.__convert_mode == CONV_MODE_ANTHY and -4 <= n <= -2:
            buf = self.__context.get_segment(self.__cursor_pos, n)
            self.__segments[self.__cursor_pos] = n, UN(buf)
            self.__lookup_table_visible = False
            self.__invalidate()
            return True

        return False

    def __cmd_convert_to_hiragana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)

        return self.__on_key_conv(0)

    def __cmd_convert_to_katakana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)

        return self.__on_key_conv(1)

    def __cmd_convert_to_half(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            i, s = self.__segments[self.__cursor_pos]
            if i == -101:
                return self.__convert_segment_to_latin(-100)
            elif i == -100:
                return self.__convert_segment_to_latin(-100)
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        elif CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
            return self.__on_key_conv(4)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__on_key_conv(4)
        return self.__on_key_conv(2)

    def __cmd_convert_to_half_katakana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        return self.__on_key_conv(2)

    def __convert_segment_to_latin(self, n):
        if self.__convert_mode == CONV_MODE_ANTHY and n in [-100, -101]:
            start = 0
            for i in range(self.__cursor_pos):
                start += len(UN(self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE)))
            end = start + len(UN(self.__context.get_segment(self.__cursor_pos, NTH_UNCONVERTED_CANDIDATE)))
            i, s = self.__segments[self.__cursor_pos]
            s2 = self.__preedit_ja_string.get_raw(start, end)
            if n == -101:
                s2 = u''.join([unichar_half_to_full(c) for c in s2])
            if i == n:
                if s == s2.lower():
                    s2 = s2.upper()
                elif s == s2.upper():
                    s2 = s2.capitalize()
                elif s == s2 or s == s2.capitalize():
                    s2 = s2.lower()
            self.__segments[self.__cursor_pos] = n, s2
            self.__lookup_table_visible = False
            self.__invalidate()
            return True

        return False

    def __cmd_convert_to_wide_latin(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
           return self.__convert_segment_to_latin(-101)

        return self.__on_key_conv(3)

    def __cmd_convert_to_latin(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
           return self.__convert_segment_to_latin(-100)

        return self.__on_key_conv(4)

    #dictonary_keys
    def __cmd_dict_admin(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_dict_admin()
        return True

    def __cmd_add_word(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_add_word()
        return True

    def __cmd_start_setup(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_setup()
        return True

    def __start_dict_admin(self):
        command = self.__prefs.get_value('common', 'dict_admin_command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_add_word(self):
        command = self.__prefs.get_value('common', 'add_word_command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_setup(self):
        if Engine.__setup_pid != 0:
            pid, state = os.waitpid(Engine.__setup_pid, os.P_NOWAIT)
            if pid != Engine.__setup_pid:
                return
            Engine.__setup_pid = 0
        setup_cmd = path.join(config.LIBEXECDIR, 'ibus-setup-anthy')
        Engine.__setup_pid = os.spawnl(os.P_NOWAIT, setup_cmd, 'ibus-setup-anthy')

