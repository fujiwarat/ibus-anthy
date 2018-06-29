# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2018 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2018 Red Hat, Inc.
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

import binascii
import io
import os
from os import environ, path
import signal
import sys
from gettext import dgettext

from main import get_userhome

try:
    from locale import getpreferredencoding
except:
    pass

from gi import require_version as gi_require_version
gi_require_version('GLib', '2.0')
gi_require_version('IBus', '1.0')
gi_require_version('Anthy', '9000')

from gi.repository import GLib
from gi.repository import IBus

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

printerr = AnthyPrefs.printerr

INPUT_MODE_HIRAGANA, \
INPUT_MODE_KATAKANA, \
INPUT_MODE_HALF_WIDTH_KATAKANA, \
INPUT_MODE_LATIN, \
INPUT_MODE_WIDE_LATIN = list(range(5))

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
CONV_MODE_PREDICTION = list(range(14))

SEGMENT_DEFAULT         = 0
SEGMENT_SINGLE          = 1 << 0
SEGMENT_IMMEDIATE       = 1 << 1

CLIPBOARD_RECONVERT = list(range(1))

LINK_DICT_EMBEDDED, \
LINK_DICT_SINGLE = list(range(2))

IMPORTED_EMBEDDED_DICT_DIR = 'imported_words_default.d'
IMPORTED_EMBEDDED_DICT_PREFIX = 'ibus__'
IMPORTED_SINGLE_DICT_PREFIX = 'imported_words_ibus__'

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

class Engine(IBus.EngineSimple):
    __input_mode = None
    __typing_mode = None
    __segment_mode = None
    __dict_mode = None

    __setup_pid = 0
    __prefs = None
    __keybind = {}
    __thumb = None
    __latin_with_shift = True

    def __init__(self, bus, object_path):
        super(Engine, self).__init__(engine_name="anthy",
                                     connection=bus.get_connection(),
                                     object_path=object_path)

        self.add_table_by_locale(None)
        # create anthy context
        if not self.__verify_anthy_journal_file():
            return
        self.__context = Anthy.GContext()
        self.__context.set_encoding(Anthy.UTF8_ENCODING)

        # init state
        self.__idle_id = 0
        self.__prop_dict = {}
        self.__input_purpose = 0
        self.__has_input_purpose = False
        if hasattr(IBus, 'InputPurpose'):
            self.__has_input_purpose = True
        try:
            self.__is_utf8 = (getpreferredencoding().lower() == 'utf-8')
        except:
            self.__is_utf8 = False
        self.__has_update_preedit_text_with_mode = True
        try:
            self.__ibus_check_version('1.3')
        except ValueError as e:
            printerr('Disable update_preedit_text_with_mode(): %s' % str(e))
            self.__has_update_preedit_text_with_mode = False

#        self.__lookup_table = ibus.LookupTable.new(page_size=9,
#                                                   cursor_pos=0,
#                                                   cursor_visible=True,
#                                                   round=True)
        size = self.__prefs.get_value('common', 'page-size')
        self.__lookup_table = IBus.LookupTable.new(page_size=size,
                                                   cursor_pos=0,
                                                   cursor_visible=True,
                                                   round=True)
        self.__prop_list = self.__init_props()

        # Do not use self.do_process_key_event to work ISO 14755
        # with Ctrl+Shift+u .
        # The super (parent) method of do_process_key_event is called
        # loop infinitely if this class overrides it.
        # self.process_key_event is not accessible too.
        self.connect('process-key-event', self.__process_key_event)
        self.connect('destroy', self.__destroy)
        self.connect('page-down', self.__page_down)
        self.connect('page-up', self.__page_up)
        self.connect('candidate-clicked', self.__candidate_clicked)

        self.__init_signal()
        # use reset to init values
        self.__reset()


    def __ibus_check_version(self, v):
        major = IBus.MAJOR_VERSION
        minor = IBus.MINOR_VERSION
        micro = IBus.MICRO_VERSION
        if (major, minor, micro) < tuple(map(int, (v.split('.')))):
            raise ValueError('Required ibus %s but version of ibus is ' \
                             '%d.%d.%d' % (v, major, minor, micro))

    # http://en.sourceforge.jp/ticket/browse.php?group_id=14&tid=33075
    def __verify_anthy_journal_file(self):
        journal = get_userhome() + '/.anthy/last-record2_default.utf8'
        try:
            f = io.open(file=journal, mode='rb')
        except IOError:
            return True
        f.seek(-1, io.SEEK_END)
        last = f.read(1)
        f.close()
        if ord(last) == 0xa:
            return True
        from gi.repository import Gtk
        message= N_("Could not enable Anthy.\n" \
                    "The end of the content of the file " \
                    ".anthy/last-record2_default.utf8 in your home " \
                    "directory is not '\\n'. I.e. not correct text format.\n" \
                    "Please fix the file or remove it by manual and " \
                    "restart IBus.")
        printerr(message)
        dlg = Gtk.MessageDialog(parent=None,
                                flags=Gtk.DialogFlags.MODAL,
                                message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK,
                                message_format=_(message))
        dlg.run()
        dlg.destroy()
        return False

    # reset values of engine
    def __reset(self):
        self.__preedit_ja_string = jastring.JaString(Engine.__typing_mode,
                                                     self.__latin_with_shift)
        self.__convert_chars = ''
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
            GLib.source_remove(self.__idle_id)
            self.__idle_id = 0

    def __init_props(self):
        anthy_props = IBus.PropList()

        self.__set_input_mode_props(anthy_props)
        self.__set_typing_method_props(anthy_props)
        self.__set_segment_mode_props(anthy_props)
        self.__set_dict_mode_props(anthy_props)
        self.__set_dict_config_props(anthy_props)

        if not self.__prefs.get_value('common', 'show-preferences'):
            return anthy_props

        anthy_props.append(IBus.Property(key='setup',
                                         label=IBus.Text.new_from_string(_("Preferences - Anthy")),
                                         icon=config.ICON_PREFERENCE,
                                         tooltip=IBus.Text.new_from_string(_("Configure Anthy")),
                                         sensitive=True,
                                         visible=True))

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

    def __set_input_mode_props(self, anthy_props):
        # The class method is kept even if the engine is switched.
        if Engine.__input_mode == None:
            # The config value is readonly for initial engine and
            # the engine keeps the class method in the memory.
            Engine.__input_mode = INPUT_MODE_HIRAGANA
            Engine.__input_mode = self.__prefs.get_value('common',
                                                         'input-mode')

        if not self.__prefs.get_value('common', 'show-input-mode'):
            return

        # init input mode properties
        symbol = 'あ'
        '''
        Need to split _() by line for intltool to detect them.
        '''
        # Translators: Specify the order of %s with your translation.
        # It will be "Input Mode (A)" for example.
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Input mode"), 'symbol' : symbol }
        input_mode_prop = IBus.Property(key='InputMode',
                                        prop_type=IBus.PropType.MENU,
                                        label=IBus.Text.new_from_string(label),
                                        symbol=IBus.Text.new_from_string(symbol),
                                        icon='',
                                        tooltip=IBus.Text.new_from_string(_("Switch input mode")),
                                        sensitive=True,
                                        visible=True,
                                        state=IBus.PropState.UNCHECKED,
                                        sub_props=None)
        self.__prop_dict['InputMode'] = input_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key='InputMode.Hiragana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Hiragana")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='InputMode.Katakana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Katakana")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='InputMode.HalfWidthKatakana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Halfwidth Katakana")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='InputMode.Latin',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Latin")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='InputMode.WideLatin',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Wide Latin")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))

        props.get(Engine.__input_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        input_mode_prop.set_sub_props(props)
        anthy_props.append(input_mode_prop)

        mode = Engine.__input_mode
        mode = 'InputMode.' + ['Hiragana', 'Katakana', 'HalfWidthKatakana',
                               'Latin', 'WideLatin'][mode]
        self.__input_mode_activate(mode, IBus.PropState.CHECKED)

    def __set_typing_method_props(self, anthy_props):
        if Engine.__typing_mode == None:
            Engine.__typing_mode = jastring.TYPING_MODE_ROMAJI
            Engine.__typing_mode = self.__prefs.get_value('common',
                                                          'typing-method')

        if not self.__prefs.get_value('common', 'show-typing-method'):
            return

        # typing input mode properties
        symbol = 'R'
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Typing method"), 'symbol' : symbol }
        typing_mode_prop = IBus.Property(key='TypingMode',
                                         prop_type=IBus.PropType.MENU,
                                         label=IBus.Text.new_from_string(label),
                                         symbol=IBus.Text.new_from_string(symbol),
                                         icon='',
                                         tooltip=IBus.Text.new_from_string(_("Switch typing method")),
                                         sensitive=True,
                                         visible=True,
                                         state=IBus.PropState.UNCHECKED,
                                         sub_props=None)
        self.__prop_dict['TypingMode'] = typing_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key='TypingMode.Romaji',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Romaji")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='TypingMode.Kana',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Kana")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='TypingMode.ThumbShift',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Thumb shift")),
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

        mode = Engine.__typing_mode
        mode = 'TypingMode.' + ['Romaji', 'Kana', 'ThumbShift'][mode]
        self.__typing_mode_activate(mode, IBus.PropState.CHECKED)

    def __set_segment_mode_props(self, anthy_props):
        if Engine.__segment_mode == None:
            Engine.__segment_mode = SEGMENT_DEFAULT
            Engine.__segment_mode = self.__prefs.get_value('common',
                                                           'conversion-segment-mode')

        if not self.__prefs.get_value('common', 'show-segment-mode'):
            return

        symbol = '連'
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Segment mode"), 'symbol' : symbol }
        segment_mode_prop = IBus.Property(key='SegmentMode',
                                          prop_type=IBus.PropType.MENU,
                                          label=IBus.Text.new_from_string(label),
                                          symbol=IBus.Text.new_from_string(symbol),
                                          icon=None,
                                          tooltip=IBus.Text.new_from_string(_("Switch conversion mode")),
                                          sensitive=True,
                                          visible=True,
                                          state=IBus.PropState.UNCHECKED,
                                          sub_props=None)
        self.__prop_dict['SegmentMode'] = segment_mode_prop

        props = IBus.PropList()
        props.append(IBus.Property(key='SegmentMode.Multi',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Multiple segment")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='SegmentMode.Single',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Single segment")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='SegmentMode.ImmediateMulti',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Immediate conversion (multiple segment)")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='SegmentMode.ImmediateSingle',
                                   prop_type=IBus.PropType.RADIO,
                                   label=IBus.Text.new_from_string(_("Immediate conversion (single segment)")),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.get(Engine.__segment_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        segment_mode_prop.set_sub_props(props)
        anthy_props.append(segment_mode_prop)

        mode = Engine.__segment_mode
        mode = 'SegmentMode.' + ['Multi', 'Single',
                                 'ImmediateMulti', 'ImmediateSingle'][mode]
        self.__segment_mode_activate(mode, IBus.PropState.CHECKED)

    def __set_dict_mode_props(self, anthy_props, update_prop=False):
        if Engine.__dict_mode == None:
            Engine.__dict_mode = 0

        if not self.__prefs.get_value('common', 'show-dict-mode'):
            return

        dicts = self.__prefs.get_value('dict', 'list')
        short_label = dicts['embedded'].short_label
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Dictionary mode"), 'symbol' : short_label }
        dict_mode_prop = IBus.Property(key='DictMode',
                                       prop_type=IBus.PropType.MENU,
                                       label=IBus.Text.new_from_string(label),
                                       symbol=IBus.Text.new_from_string(short_label),
                                       icon=None,
                                       tooltip=IBus.Text.new_from_string(_("Switch dictionary")),
                                       sensitive=True,
                                       visible=True,
                                       state=IBus.PropState.UNCHECKED,
                                       sub_props=None)
        self.__prop_dict['DictMode'] = dict_mode_prop
        props = IBus.PropList()

        long_label = dicts['embedded'].long_label
        props.append(IBus.Property(key='DictMode.embedded',
                                   prop_type=IBus.PropType.RADIO,
                                   # if long_label is UTF-8
                                   label=IBus.Text.new_from_string(_(long_label)),
                                   icon=None,
                                   tooltip=None,
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        order = self.__prefs.get_value('dict', 'order')
        if len(order) == 0:
            order = list(self.__prefs.get_value('dict', 'files').keys())
        files = self.__prefs.get_value('dict', 'files')
        dicts = self.__prefs.get_value('dict', 'list')
        for id in order:
            dict_item = dicts[id]
            is_cont = False
            for file in files[id]:
                if not self.__link_dict_file(dict_item, file):
                    is_cont = True
                    break
            if is_cont:
                  continue
            if not dict_item.single:
                  continue
            key = 'DictMode.' + id
            long_label = dict_item.long_label

            # ibus-config 'value-changed' signal updated dict/files but
            # not dict/file/new yet.
            if long_label == None:
                continue

            if dict_item.is_system:
                uni_long_label = _(long_label)
            else:
                uni_long_label = long_label
            props.append(IBus.Property(key=key,
                                       prop_type=IBus.PropType.RADIO,
                                       label=IBus.Text.new_from_string(uni_long_label),
                                       icon=None,
                                       tooltip=None,
                                       sensitive=True,
                                       visible=True,
                                       state=IBus.PropState.UNCHECKED,
                                       sub_props=None))

        props.get(Engine.__dict_mode).set_state(IBus.PropState.CHECKED)

        i = 0
        while props.get(i) != None:
            prop = props.get(i)
            self.__prop_dict[prop.get_key()] = prop
            i += 1

        dict_mode_prop.set_sub_props(props)

        if update_prop:
            # focus-in event will call register_properties().
            # Need to switch another IME to update menus on GtkStatusIcon?
            anthy_props.update_property(dict_mode_prop)
        else:
            anthy_props.append(dict_mode_prop)

        prop_name = self.__dict_mode_get_prop_name(Engine.__dict_mode)
        if prop_name == None:
            return
        self.__dict_mode_activate(prop_name,
                                  IBus.PropState.CHECKED)

    def __set_dict_config_props(self, anthy_props):
        if not self.__prefs.get_value('common', 'show-dict-config'):
            return

        admin_command = self.__prefs.get_value('common', 'dict-admin-command')
        icon_path = self.__prefs.get_value('common', 'dict-config-icon')

        if not path.exists(admin_command[0]):
            return
        label = _("Dictionary - Anthy")
        if icon_path and path.exists(icon_path):
            icon = icon_path
        else:
            # Translators: "Dic" means 'dictionary', One kanji may be good.
            label = _("Dic")
            icon = ''

        dict_prop = IBus.Property(key='setup-dict-kasumi',
                                  prop_type=IBus.PropType.MENU,
                                  label=IBus.Text.new_from_string(label),
                                  icon=icon,
                                  tooltip=IBus.Text.new_from_string(_("Configure dictionaries")),
                                  sensitive=True,
                                  visible=True,
                                  state=IBus.PropState.UNCHECKED,
                                  sub_props=None)
        self.__prop_dict['setup-dict-kasumi'] = dict_prop

        props = IBus.PropList()
        props.append(IBus.Property(key='setup-dict-kasumi-admin',
                                   prop_type=IBus.PropType.NORMAL,
                                   label=IBus.Text.new_from_string(_("Edit dictionaries")),
                                   icon=icon,
                                   tooltip=IBus.Text.new_from_string(_("Launch the dictionary tool")),
                                   sensitive=True,
                                   visible=True,
                                   state=IBus.PropState.UNCHECKED,
                                   sub_props=None))
        props.append(IBus.Property(key='setup-dict-kasumi-word',
                                   prop_type=IBus.PropType.NORMAL,
                                   label=IBus.Text.new_from_string(_("Add words")),
                                   icon=icon,
                                   tooltip=IBus.Text.new_from_string(_("Add words to the dictionary")),
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
        order = self.__prefs.get_value('dict', 'order')
        if len(order) == 0:
            order = list(self.__prefs.get_value('dict', 'files').keys())
        files = self.__prefs.get_value('dict', 'files')
        dicts = self.__prefs.get_value('dict', 'list')
        single_files = []
        for id in order:
            for file in files[id]:
                if not path.exists(file):
                    continue
                dict_item = dicts[id]
                if dict_item.single:
                    single_files.append(file)
        return single_files

    def __remove_dict_files(self):
        dicts = self.__prefs.get_value('dict', 'list')
        files = self.__prefs.get_value('dict', 'files')
        for id in files.keys():
            dict_item = dicts[id]
            for file in files[id]:
                self.__remove_dict_file(dict_item, file)

    def update_preedit(self, string, attrs, cursor_pos, visible):
        text = IBus.Text.new_from_string(string)
        i = 0
        while attrs.get(i) != None:
            attr = attrs.get(i)
            text.append_attribute(attr.get_attr_type(),
                                  attr.get_value(),
                                  attr.get_start_index(),
                                  attr.get_end_index())
            i += 1
        mode = self.__prefs.get_value('common', 'behavior-on-focus-out')
        if self.__has_update_preedit_text_with_mode and mode == 1:
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

    def __page_up(self, obj):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_up():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = self.__lookup_table.get_candidate(index).get_text()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def __page_down(self, obj):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_down():
            return False

        index = self.__lookup_table.get_cursor_pos()
        candidate = self.__lookup_table.get_candidate(index).get_text()
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
        candidate = self.__lookup_table.get_candidate(index).get_text()
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
        candidate = self.__lookup_table.get_candidate(index).get_text()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def __candidate_clicked(self, obj, index, button, state):
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
        for i in range(self.__cursor_pos, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = buf
            self.__segments.append((0, text))
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def __shrink_segment_end(self):
        while self.__context.get_nr_segments() > 1:
            self.__context.resize_segment(self.__cursor_pos, 1)
            nr_segments = self.__context.get_nr_segments()
            del self.__segments[self.__cursor_pos:]
            for i in range(self.__cursor_pos, nr_segments):
                buf = self.__context.get_segment(i, 0)
                text = buf
                self.__segments.append((0, text))
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def do_property_activate(self, prop_name, state):

        if state == IBus.PropState.CHECKED:
            if prop_name == None:
                return
            elif prop_name.startswith('InputMode.'):
                self.__input_mode_activate(prop_name, state)
                return
            elif prop_name.startswith('TypingMode.'):
                self.__typing_mode_activate(prop_name, state)
                return
            elif prop_name.startswith('SegmentMode.'):
                self.__segment_mode_activate(prop_name, state)
                return
            elif prop_name.startswith('DictMode.'):
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
                if prop_name not in self.__prop_dict.keys():
                    return
                self.__prop_dict[prop_name].set_state(state)
                if prop_name == 'DictMode':
                    sub_name = self.__dict_mode_get_prop_name(self.__dict_mode)
                    if sub_name == None:
                        return
                    self.__dict_mode_activate(sub_name,
                                              IBus.PropState.CHECKED)

    def __input_mode_activate(self, prop_name, state):
        input_modes = {
            'InputMode.Hiragana' : (INPUT_MODE_HIRAGANA, 'あ'),
            'InputMode.Katakana' : (INPUT_MODE_KATAKANA, 'ア'),
            'InputMode.HalfWidthKatakana' : (INPUT_MODE_HALF_WIDTH_KATAKANA, '_ｱ'),
            'InputMode.Latin' : (INPUT_MODE_LATIN, '_A'),
            'InputMode.WideLatin' : (INPUT_MODE_WIDE_LATIN, 'Ａ'),
        }

        if prop_name not in input_modes:
            printerr('Unknown prop_name = %s' % prop_name)
            return
        mode, symbol = input_modes[prop_name]
        if 'InputMode' not in self.__prop_dict.keys():
            # Disable to show input mode with ibus-set-anthy
            Engine.__input_mode = mode
            return

        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Input mode"), 'symbol' : symbol }
        Engine.__input_mode = mode
        prop = self.__prop_dict['InputMode']
        prop.set_symbol(IBus.Text.new_from_string(symbol))
        prop.set_label(IBus.Text.new_from_string(label))
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __typing_mode_activate(self, prop_name, state):
        if 'TypingMode' not in self.__prop_dict.keys():
            # Disable to show typing mode with ibus-set-anthy
            return
        typing_modes = {
            'TypingMode.Romaji' : (jastring.TYPING_MODE_ROMAJI, 'R'),
            'TypingMode.Kana' : (jastring.TYPING_MODE_KANA, 'か'),
            'TypingMode.ThumbShift' : (jastring.TYPING_MODE_THUMB_SHIFT, '親'),
        }

        if prop_name not in typing_modes:
            printerr('Unknown prop_name = %s' % prop_name)
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        if prop_name == 'TypingMode.ThumbShift':
            self._reset_thumb()

        mode, symbol = typing_modes[prop_name]

        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Typing method"), 'symbol' : symbol }
        Engine.__typing_mode = mode
        prop = self.__prop_dict['TypingMode']
        prop.set_symbol(IBus.Text.new_from_string(symbol))
        prop.set_label(IBus.Text.new_from_string(label))
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __refresh_typing_mode_property(self):
        if 'TypingMode' not in self.__prop_dict:
            # Disable to show typing mode with ibus-set-anthy
            return
        prop = self.__prop_dict['TypingMode']
        modes = {
            jastring.TYPING_MODE_ROMAJI : ('TypingMode.Romaji', 'R'),
            jastring.TYPING_MODE_KANA : ('TypingMode.Kana', 'か'),
            jastring.TYPING_MODE_THUMB_SHIFT : ('TypingMode.ThumbShift', '親'),
        }
        prop_name, symbol = modes.get(Engine.__typing_mode, (None, None))
        if prop_name == None or symbol == None:
            return
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Typing method"), 'symbol' : symbol }
        _prop = self.__prop_dict[prop_name]
        _prop.set_state(IBus.PropState.CHECKED)
        self.update_property(_prop)
        prop.set_symbol(IBus.Text.new_from_string(symbol))
        prop.set_label(IBus.Text.new_from_string(label))
        self.update_property(prop)

    def __segment_mode_activate(self, prop_name, state):
        if 'SegmentMode' not in self.__prop_dict.keys():
            # Disable to show segment mode with ibus-set-anthy
            return
        segment_modes = {
            'SegmentMode.Multi' : (SEGMENT_DEFAULT, '連'),
            'SegmentMode.Single' : (SEGMENT_SINGLE, '単'),
            'SegmentMode.ImmediateMulti' : (SEGMENT_IMMEDIATE, '逐|連'),
            'SegmentMode.ImmediateSingle' :
                (SEGMENT_IMMEDIATE | SEGMENT_SINGLE, '逐|単'),
        }

        if prop_name not in segment_modes:
            printerr('Unknown prop_name = %s' % prop_name)
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        mode, symbol = segment_modes[prop_name]

        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Segment mode"), 'symbol' : symbol }
        Engine.__segment_mode = mode
        prop = self.__prop_dict['SegmentMode']
        prop.set_symbol(IBus.Text.new_from_string(symbol))
        prop.set_label(IBus.Text.new_from_string(label))
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __dict_mode_get_prop_name(self, mode):
        if mode == 0:
            id = 'embedded'
        else:
            single_files = self.__get_single_dict_files()
            file = single_files[mode - 1]
            id = self.__get_dict_id_from_file(file)
        return 'DictMode.' + id

    def __dict_mode_activate(self, prop_name, state):
        if prop_name not in list(self.__prop_dict.keys()):
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
        else:
            found = False
            for file in single_files:
                if id == self.__get_quoted_id(file):
                    found = True
                    break
            if found == False:
                return

        if id == 'embedded':
            dict_name = 'default'
            Engine.__dict_mode = 0
        else:
            if file not in single_files:
                printerr('Index error', file, single_files)
                return
            dict_name = 'ibus__' + id
            Engine.__dict_mode = single_files.index(file) + 1
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        self.__context.init_personality()
        # dict_name is unicode but the argument is str.
        self.__context.do_set_personality(str(dict_name))

        prop = self.__prop_dict['DictMode']
        dicts = self.__prefs.get_value('dict', 'list')
        symbol = dicts[id].short_label
        label = _("%(description)s (%(symbol)s)") % \
            { 'description' : _("Dictionary mode"), 'symbol' : symbol }
        prop.set_symbol(IBus.Text.new_from_string(symbol))
        prop.set_label(IBus.Text.new_from_string(label))
        self.update_property(prop)

    def __argb(self, a, r, g, b):
        return ((a & 0xff)<<24) + ((r & 0xff) << 16) + ((g & 0xff) << 8) + (b & 0xff)

    def __rgb(self, r, g, b):
        return self.__argb(255, r, g, b)

    def do_focus_in(self):
        self.register_properties(self.__prop_list)
        self.__refresh_typing_mode_property()
        mode = self.__prefs.get_value('common', 'behavior-on-focus-out')
        if mode == 2:
            self.__update_input_chars()
#        self.__reset()
#        self.__invalidate()
        size = self.__prefs.get_value('common', 'page-size')
        if size != self.__lookup_table.get_page_size():
            self.__lookup_table.set_page_size(size)

    def do_focus_out(self):
        if self.__has_input_purpose:
            self.__input_purpose = 0
        mode = self.__prefs.get_value('common', 'behavior-on-focus-out')
        if mode == 0 or mode == 1:
            self.__reset()
            self.__invalidate()

    def do_set_content_type(self, purpose, hints):
        if self.__has_input_purpose:
            self.__input_purpose = purpose

    def do_disable(self):
        self.__reset()
        self.__invalidate()

    def do_reset(self):
        self.__reset()
        self.__invalidate()

    def __destroy(self, obj):
        if self.__idle_id != 0:
            GLib.source_remove(self.__idle_id)
            self.__idle_id = 0
        # It seems do_destroy() is called when launch_engine() is called.
        #self.__remove_dict_files()
        # It seems super.destroy() does not unref the engine.

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
        for key in list(romaji_normalize_rule.keys()):
            if preedit.find(key) >= 0:
                for value in romaji_normalize_rule[key]:
                    preedit = preedit.replace(key, value)
        return preedit

    # begine convert
    def __begin_anthy_convert(self):
        if Engine.__segment_mode & SEGMENT_IMMEDIATE:
            self.__end_anthy_convert()
        if self.__convert_mode == CONV_MODE_ANTHY:
            return
        self.__convert_mode = CONV_MODE_ANTHY

#        text, cursor = self.__preedit_ja_string.get_hiragana()
        text, cursor = self.__preedit_ja_string.get_hiragana(True)

        text = self.__normalize_preedit(text)
        self.__context.set_string(text)
        if Engine.__segment_mode & SEGMENT_SINGLE:
            self.__join_all_segments()
        nr_segments = self.__context.get_nr_segments()

        for i in range(0, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = buf
            self.__segments.append((0, text))

        if Engine.__segment_mode & SEGMENT_IMMEDIATE:
            self.__cursor_pos = nr_segments - 1
        else:
            self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False

    def __end_anthy_convert(self):
        if self.__convert_mode == CONV_MODE_OFF:
            return

        self.__convert_mode = CONV_MODE_OFF
        self.__convert_chars = ''
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
        for key in list(romaji_utf8_rule.keys()):
            if candidate.find(key) >= 0:
                for value in romaji_utf8_rule[key]:
                    candidate = candidate.replace(key, value)
                    self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))

    def __fill_lookup_table(self):
        if self.__convert_mode == CONV_MODE_PREDICTION:
            nr_predictions = self.__context.get_nr_predictions()

            # fill lookup_table
            self.__lookup_table.clear()
            for i in range(0, nr_predictions):
                buf = self.__context.get_prediction(i)
                candidate = buf
                self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))
                self.__candidate_cb(candidate)
            return

        # get segment stat
        nr_candidates = self.__context.get_nr_candidates(self.__cursor_pos)

        # fill lookup_table
        self.__lookup_table.clear()
        for i in range(0, nr_candidates):
            buf = self.__context.get_segment(self.__cursor_pos, i)
            candidate = buf
            self.__lookup_table.append_candidate(IBus.Text.new_from_string(candidate))
            self.__candidate_cb(candidate)


    def __invalidate(self):
        if self.__idle_id != 0:
            return
        self.__idle_id = GLib.idle_add(self.__update,
                                       priority = GLib.PRIORITY_LOW)

#    def __get_preedit(self):
    def __get_preedit(self, commit=False):
        if Engine.__input_mode == INPUT_MODE_HIRAGANA:
#            text, cursor = self.__preedit_ja_string.get_hiragana()
            text, cursor = self.__preedit_ja_string.get_hiragana(commit)
        elif Engine.__input_mode == INPUT_MODE_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_katakana()
            text, cursor = self.__preedit_ja_string.get_katakana(commit)
        elif Engine.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
            text, cursor = self.__preedit_ja_string.get_half_width_katakana(commit)
        else:
            text, cursor = '', 0
        return text, cursor

    def __update_input_chars(self):
        text, cursor = self.__get_preedit()
        attrs = IBus.AttrList()
        attrs.append(IBus.attr_underline_new(
            IBus.AttrUnderline.SINGLE, 0,
            len(text)))

        self.update_preedit(text,
            attrs, cursor, not self.__preedit_ja_string.is_empty())
        self.update_aux_string('', IBus.AttrList(), False)
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
        attrs = IBus.AttrList()
        attrs.append(IBus.attr_underline_new(
            IBus.AttrUnderline.SINGLE, 0, len(text)))
        attrs.append(IBus.attr_background_new(self.__rgb(200, 200, 240),
            0, len(text)))
        attrs.append(IBus.attr_foreground_new(self.__rgb(0, 0, 0),
            0, len(text)))
        self.update_preedit(text, attrs, len(text), True)

        self.update_aux_string('',
            IBus.AttrList(), self.__lookup_table_visible)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update_anthy_convert_chars(self):
        self.__convert_chars = ''
        pos = 0
        for i, (seg_index, text) in enumerate(self.__segments):
            self.__convert_chars += text
            if i < self.__cursor_pos:
                pos += len(text)
        attrs = IBus.AttrList()
        attrs.append(IBus.attr_underline_new(
            IBus.AttrUnderline.SINGLE, 0, len(self.__convert_chars)))
        attrs.append(IBus.attr_background_new(self.__rgb(200, 200, 240),
                pos, pos + len(self.__segments[self.__cursor_pos][1])))
        attrs.append(IBus.attr_foreground_new(self.__rgb(0, 0, 0),
                pos, pos + len(self.__segments[self.__cursor_pos][1])))
        self.update_preedit(self.__convert_chars, attrs, pos, True)
        aux_string = '( %d / %d )' % (self.__lookup_table.get_cursor_pos() + 1, self.__lookup_table.get_number_of_candidates())
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
                if self.__lookup_table.get_number_of_candidates() > 0:
                    self.__lookup_table.set_cursor_pos(0)
                candidate = self.__lookup_table.get_candidate(0).get_text()
                self.__segments[self.__cursor_pos] = 0, candidate
                self.__lookup_table_visible = False
            elif self.__segments[self.__cursor_pos][0] != \
                    NTH_UNCONVERTED_CANDIDATE:
                buf = self.__context.get_segment(self.__cursor_pos,
                                                 NTH_UNCONVERTED_CANDIDATE)
                self.__segments[self.__cursor_pos] = \
                    NTH_UNCONVERTED_CANDIDATE, buf
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
                all_text = ''
                nr_segments = self.__context.get_nr_segments()
                for i in xrange(0, nr_segments):
                    buf = self.__context.get_segment(i,
                                                     NTH_UNCONVERTED_CANDIDATE)
                    text = buf
                    if i == self.__cursor_pos and len(text) > 0:
                        text = text[:len(text) - 1]
                    all_text += text

                if all_text == '':
                    return

                # Set self.__preedit_ja_string by anthy context.
                self.__preedit_ja_string = jastring.JaString(Engine.__typing_mode,
                                                             self.__latin_with_shift)
                self.__convert_chars = self.__normalize_preedit(all_text)
                for i in xrange(0, len(self.__convert_chars)):
                    keyval = self.__convert_chars[i]
                    self.__preedit_ja_string.insert(chr(ord(keyval)))
                self.__context.set_string(self.__convert_chars)

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
                    text = buf
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

        if Engine.__input_mode >= INPUT_MODE_HIRAGANA and \
           Engine.__input_mode < INPUT_MODE_HALF_WIDTH_KATAKANA:
            Engine.__input_mode += 1
        else:
            Engine.__input_mode = INPUT_MODE_HIRAGANA

        modes = { INPUT_MODE_HIRAGANA: 'あ',
                  INPUT_MODE_KATAKANA: 'ア',
                  INPUT_MODE_HALF_WIDTH_KATAKANA: '_ｱ' }

        prop = self.__prop_dict[u'InputMode']
        label = modes[Engine.__input_mode]
        prop.set_label(IBus.Text.new_from_string(label))
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
        if Engine.__input_mode == INPUT_MODE_WIDE_LATIN or wide:
            # Input Wide space U+3000
            wide_char = symbol_rule[chr(IBus.KEY_space)]
            self.__commit_string(wide_char)
            return True

        if self.__preedit_ja_string.is_empty():
            if Engine.__input_mode in (INPUT_MODE_HIRAGANA, INPUT_MODE_KATAKANA):
                # Input Wide space U+3000
                wide_char = symbol_rule[chr(IBus.KEY_space)]
                self.__commit_string(wide_char)
                return True
            else:
                # Input Half space U+0020
                self.__commit_string(chr(IBus.KEY_space))
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
            printerr('Unkown convert mode (%d)!' % mode)
            return False
        self.__invalidate()
        return True

    def __on_key_common(self, keyval, state=0):

        # If use-system-layout is FALSE in ibus 1.4.y or lower,
        # ibus converts the keymap and ibus-anthy needed to use
        # self.__commit_string
        # ibus 1.5.y uses XKB directly so Latin mode can return FALSE.
        if Engine.__input_mode == INPUT_MODE_LATIN:
            return False

        elif Engine.__input_mode == INPUT_MODE_WIDE_LATIN:
            #  Input Wide Latin chars
            char = chr(keyval)
            wide_char = None#symbol_rule.get(char, None)
            if wide_char == None:
                wide_char = unichar_half_to_full(char)
            self.__commit_string(wide_char)
            return True

        # Input Japanese
        if Engine.__segment_mode & SEGMENT_IMMEDIATE:
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
        self.__preedit_ja_string.insert(chr(keyval))
        if Engine.__segment_mode & SEGMENT_IMMEDIATE:
            self.__begin_anthy_convert()
        self.__invalidate()
        return True

#=======================================================================
    @classmethod
    def CONFIG_RELOADED(cls):
        if config.DEBUG:
            print('RELOADED')
        if not cls.__prefs:
            cls.__prefs = AnthyPrefs()
            cls.__prefs.connect('changed', cls.CONFIG_VALUE_CHANGED)
            cls._init_prefs()

        cls.__keybind = cls._mk_keybind()

        jastring.JaString.SET_PREFS(cls.__prefs)

    @classmethod
    def CONFIG_VALUE_CHANGED(cls, prefs, section, key, variant):
        if config.DEBUG:
            print('VALUE_CHAMGED =', section, key, variant)
        if section == 'shortcut':
            cls.__keybind = cls._mk_keybind()
        elif section == 'common':
            if key == 'shortcut-type':
                cls.__keybind = cls._mk_keybind()
            elif key == 'latin-with-shift':
                value = prefs.get_value(section, key)
                cls.__latin_with_shift = value
                jastring.JaString.RESET(cls.__prefs, section, key, value)
        elif section == 'kana-typing-rule':
            value = prefs.get_value(section, key)
            jastring.JaString.RESET(cls.__prefs, section, key, value)

    @classmethod
    def _init_prefs(cls):
        prefs = cls.__prefs
        value = prefs.get_value('common', 'latin-with-shift')
        cls.__latin_with_shift = value

    @classmethod
    def _mk_keybind(cls):
        keybind = {}
        sec = cls._get_shortcut_type()
        shortcuts = cls.__prefs.get_value('shortcut', sec)
        for k in shortcuts.keys():
            cmd = '_Engine__cmd_' + k
            for s in shortcuts[k]:
                keybind.setdefault(cls._s_to_key(s), []).append(cmd)
        return keybind

    @classmethod
    def _get_shortcut_type(cls):
        try:
            t = cls.__prefs.get_value('common', 'shortcut-type')
        except:
            t = 'default'
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

    @staticmethod
    def _mk_key(keyval, state):
        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
            if keyval < 0xff and \
               chr(keyval) in '!"#$%^\'()*+,-./:;<=>?@[\]^_`{|}~':
                state |= IBus.ModifierType.SHIFT_MASK
            elif IBus.KEY_a <= keyval <= IBus.KEY_z:
                keyval -= (IBus.KEY_a - IBus.KEY_A)

        return repr([int(state), int(keyval)])

    def __process_key_event(self, obj, keyval, keycode, state):
        try:
            return self.__process_key_event_internal2(keyval, keycode, state)
        except:
            import traceback
            traceback.print_exc()
            return False

    def __process_key_event_thumb(self, keyval, keycode, state):
        if self.__thumb == None:
            self._reset_thumb()

        def on_timeout(keyval):
            if self._MM:
                insert(self.__thumb.get_char(self._MM)[self._SS])
            else:
                cmd_exec([0, RS(), LS()][self._SS])
            self._H = None

        def start(t):
            self._H = GLib.timeout_add(t, on_timeout, keyval)

        def stop():
            if self._H:
                GLib.source_remove(self._H)
                self._H = None
                return True
            return False

        def insert(keyval):
            try:
                self._MM = self._SS = 0
                ret = self.__on_key_common(ord(keyval))
                if (keyval in
                    self.__prefs.get_value('common', 'trigger-periods')):
                    behavior = self.__prefs.get_value('common',
                                                      'behavior-on-period')
                    if behavior == 1:
                        return self.__cmd_convert(keyval, state)
                    elif behavior == 2:
                        return self.__cmd_commit(keyval, state)
                return ret
            except:
                pass

        def cmd_exec(keyval, state=0):
            key = self._mk_key(keyval, state)
            for cmd in self.__keybind.get(key, []):
                if config.DEBUG:
                    print('cmd =', cmd)
                try:
                    if getattr(self, cmd)(keyval, state):
                        return True
                except Exception as err:
                    printerr('Error command: %s: %s' % (cmd, str(err)))
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
                                                         'ten-key-mode'):
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
                        insert(self.__thumb.get_shift_char(keyval, chr(keyval)))
                    elif self._SS == 0:
                        insert(chr(keyval))
                else:
                    if not self.__preedit_ja_string.is_empty():
                        return True
                    return False
        return True

    def __process_key_event_internal2(self, keyval, keycode, state):
        if self.__has_input_purpose and \
           self.__input_purpose == IBus.InputPurpose.PASSWORD:
            return False

        if Engine.__typing_mode == jastring.TYPING_MODE_THUMB_SHIFT and \
           Engine.__input_mode not in [INPUT_MODE_LATIN, INPUT_MODE_WIDE_LATIN]:
            return self.__process_key_event_thumb(keyval, keycode, state)

        is_press = (state & IBus.ModifierType.RELEASE_MASK) == 0

        state = state & (IBus.ModifierType.SHIFT_MASK |
                         IBus.ModifierType.CONTROL_MASK |
                         IBus.ModifierType.MOD1_MASK)

        # ignore key release events
        if not is_press:
            return False

        if keyval in KP_Table and self.__prefs.get_value('common',
                                                         'ten-key-mode'):
            keyval = KP_Table[keyval]

        key = self._mk_key(keyval, state)
        for cmd in self.__keybind.get(key, []):
            if config.DEBUG:
                print('cmd =', cmd)
            try:
                if getattr(self, cmd)(keyval, state):
                    return True
            except Exception as err:
                printerr('Error command: %s: %s' % (cmd, str(err)))

        # If input mode is not LATIN, eat Ctrl+Shift+u
        hex_mod_mask = IBus.ModifierType.SHIFT_MASK | \
                       IBus.ModifierType.CONTROL_MASK
        if Engine.__input_mode != INPUT_MODE_LATIN and \
           keyval == IBus.KEY_U and \
           state & hex_mod_mask == hex_mod_mask:
            return True

        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
            return False

        if (IBus.KEY_exclam <= keyval <= IBus.KEY_asciitilde or
            keyval == IBus.KEY_yen):
            if Engine.__typing_mode == jastring.TYPING_MODE_KANA:
                if keyval == IBus.KEY_0 and state == IBus.ModifierType.SHIFT_MASK:
                    keyval = IBus.KEY_asciitilde
                elif keyval == IBus.KEY_backslash and keycode in [132-8, 133-8]:
                    keyval = IBus.KEY_yen
            ret = self.__on_key_common(keyval, state)
            if (Engine.__input_mode != INPUT_MODE_LATIN and
                chr(keyval) in
                self.__prefs.get_value('common', 'trigger-periods')):
                behavior = self.__prefs.get_value('common',
                                                  'behavior-on-period')
                if behavior == 1:
                    return self.__cmd_convert(keyval, state)
                elif behavior == 2:
                    return self.__cmd_commit(keyval, state)
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

    def __get_quoted_id(self, file):
        id = file
        has_mbcs = False

        for i in range(0, len(id)):
            if ord(id[i]) >= 0x7f:
                    has_mbcs = True
                    break
        if has_mbcs:
            id = str(binascii.hexlify(id.encode()), 'ascii')

        if id.find('/') >=0:
            id = id[id.rindex('/') + 1:]
        if id.find('.') >=0:
            id = id[:id.rindex('.')]

        if id.startswith('0x'):
            id = str(binascii.hexlify(id.encode()), 'ascii')
            has_mbcs = True
        if has_mbcs:
            id = '0x' + id
        return id

    def __get_dict_id_from_file(self, file):
        return self.__get_quoted_id(file)

    def __link_dict_file_with_mode(self, id, file, link_mode):
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = get_userhome() + '/.anthy/' + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = get_userhome() + '/.anthy'
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                printerr(directory + ' is not a directory')
                return
        else:
            os.makedirs(directory, 0o700)
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            if path.islink(directory + '/' + name):
                printerr('Removing ' + name)
                os.unlink(directory + '/' + name)
            else:
                alternate = name + str(os.getpid())
                printerr('Moving ' + name + ' to ' + alternate)
                os.rename(name, alternate)
        os.symlink(file, directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    def __remove_dict_file_with_mode(self, id, file, link_mode):
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = get_userhome() + '/.anthy/' + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = get_userhome() + '/.anthy'
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                printerr(directory + ' is not a directory')
                return
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            os.unlink(directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    def __link_dict_file(self, dict_item, file):
        if not path.exists(file):
            printerr(file + ' does not exist')
            return False
        id = dict_item.id
        if dict_item.embed:
            self.__link_dict_file_with_mode(id, file, LINK_DICT_EMBEDDED)
        if dict_item.single:
            self.__link_dict_file_with_mode(id, file, LINK_DICT_SINGLE)
        return True

    def __remove_dict_file(self, dict_item, file):
        id = dict_item.id
        if dict_item.embed:
            self.__remove_dict_file_with_mode(id, file, LINK_DICT_EMBEDDED)
        if dict_item.single:
            self.__remove_dict_file_with_mode(id, file, LINK_DICT_SINGLE)

    #mod_keys
    def __set_input_mode(self, mode):
        self.__input_mode_activate(mode, IBus.PropState.CHECKED)
        self.__reset()
        self.__invalidate()

        return True

    def __unset_current_input_mode(self):
        modes = {
            INPUT_MODE_HIRAGANA: 'InputMode.Hiragana',
            INPUT_MODE_KATAKANA: 'InputMode.Katakana',
            INPUT_MODE_HALF_WIDTH_KATAKANA: 'InputMode.HalfWidthKatakana',
            INPUT_MODE_LATIN: 'InputMode.Latin',
            INPUT_MODE_WIDE_LATIN: 'InputMode.WideLatin'
        }
        self.__input_mode_activate(modes[Engine.__input_mode],
                                   IBus.PropState.UNCHECKED)

    def __cmd_on_off(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        if Engine.__input_mode == INPUT_MODE_LATIN:
            return self.__set_input_mode('InputMode.Hiragana')
        else:
            return self.__set_input_mode('InputMode.Latin')

    def __cmd_circle_input_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: 'InputMode.Katakana',
            INPUT_MODE_KATAKANA: 'InputMode.HalfWidthKatakana',
            INPUT_MODE_HALF_WIDTH_KATAKANA: 'InputMode.Latin',
            INPUT_MODE_LATIN: 'InputMode.WideLatin',
            INPUT_MODE_WIDE_LATIN: 'InputMode.Hiragana'
        }
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode(modes[Engine.__input_mode])

    def __cmd_circle_kana_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: 'InputMode.Katakana',
            INPUT_MODE_KATAKANA: 'InputMode.HalfWidthKatakana',
            INPUT_MODE_HALF_WIDTH_KATAKANA: 'InputMode.Hiragana',
            INPUT_MODE_LATIN: 'InputMode.Hiragana',
            INPUT_MODE_WIDE_LATIN: 'InputMode.Hiragana'
        }
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode(modes[Engine.__input_mode])

    def __cmd_latin_mode(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode('InputMode.Latin')

    def __cmd_wide_latin_mode(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode('InputMode.WideLatin')

    def __cmd_hiragana_mode(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode('InputMode.Hiragana')

    def __cmd_katakana_mode(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode('InputMode.Katakana')

    def __cmd_half_katakana(self, keyval, state):
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_input_mode()
        return self.__set_input_mode('InputMode.HalfWidthKatakana')

#    def __cmd_cancel_pseudo_ascii_mode_key(self, keyval, state):
#        pass

    def __unset_current_typing_mode(self):
        modes = {
            jastring.TYPING_MODE_ROMAJI: 'TypingMode.Romaji',
            jastring.TYPING_MODE_KANA: 'TypingMode.Kana',
            jastring.TYPING_MODE_THUMB_SHIFT: 'TypingMode.ThumbShift',
        }
        self.__typing_mode_activate(modes[Engine.__typing_mode],
                                    IBus.PropState.UNCHECKED)

    def __cmd_circle_typing_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        modes = {
            jastring.TYPING_MODE_THUMB_SHIFT: 'TypingMode.Romaji',
            jastring.TYPING_MODE_KANA: 'TypingMode.ThumbShift',
            jastring.TYPING_MODE_ROMAJI: 'TypingMode.Kana',
        }
        # ibus 1.5 or later needs to send UNCHECKED
        self.__unset_current_typing_mode()
        self.__typing_mode_activate(modes[Engine.__typing_mode],
                                    IBus.PropState.CHECKED)
        return True

    def __cmd_circle_dict_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        # ibus 1.5 or later needs to send UNCHECKED
        prop_name = self.__dict_mode_get_prop_name(Engine.__dict_mode)
        if prop_name != None:
            self.__dict_mode_activate(prop_name,
                                      IBus.PropState.UNCHECKED)

        single_files = self.__get_single_dict_files()
        new_mode = Engine.__dict_mode + 1
        if new_mode > len(single_files):
            new_mode = 0
        Engine.__dict_mode = new_mode
        prop_name = self.__dict_mode_get_prop_name(Engine.__dict_mode)
        if prop_name == None:
            return False
        self.__dict_mode_activate(prop_name,
                                  IBus.PropState.CHECKED)
        return True

    #edit_keys
    def __cmd_insert_space(self, keyval, state):
        if Engine.__input_mode == INPUT_MODE_LATIN:
            return False
        if (self.__prefs.get_value('common', 'half-width-space') or
            Engine.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA):
            return self.__cmd_insert_half_space(keyval, state)
        else:
            return self.__cmd_insert_wide_space(keyval, state)

    def __cmd_insert_alternate_space(self, keyval, state):
        if Engine.__input_mode == INPUT_MODE_LATIN:
            return False
        if (self.__prefs.get_value('common', 'half-width-space') or
            Engine.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA):
            return self.__cmd_insert_wide_space(keyval, state)
        else:
            return self.__cmd_insert_half_space(keyval, state)

    def __cmd_insert_half_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        self.__commit_string(chr(IBus.KEY_space))
        return True

    def __cmd_insert_wide_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        char = chr(IBus.KEY_space)
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

        self.__context.set_prediction_string(text)
        nr_predictions = self.__context.get_nr_predictions()

#        for i in range(nr_predictions):
#            print self.__context.get_prediction(i)

        buf = self.__context.get_prediction(0)
        if not buf:
            return False

        text = buf
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

        # Move importing Gtk into Engine from the header
        # because ibus-engine-anthy --xml does not requre to open X.
        try:
            from gi.repository import Gtk
            clipboard_get = Gtk.Clipboard.get
        except ImportError:
            clipboard_get = lambda a : None
        except RuntimeError:
            # Do we support the engine without display?
            printerr("Gtk couldn't be initialized")
            printerr('Could not open display')
            clipboard_get = lambda a : None

        # Use Gtk.Clipboard.request_text() instead of
        # Gtk.Clipboard.wait_for_text() because DBus is timed out.
        clipboard = clipboard_get ('PRIMARY')
        if clipboard:
            clipboard.request_text (self.__get_clipboard, CLIPBOARD_RECONVERT)

        return True

    def __update_reconvert(self, clipboard_text):
        if clipboard_text == None:
            return False

        self.__convert_chars = clipboard_text
        for i in range(0, len(self.__convert_chars)):
            keyval = self.__convert_chars[i]
            self.__preedit_ja_string.insert(chr(ord(keyval)))

        self.__context.set_string(self.__convert_chars)
        nr_segments = self.__context.get_nr_segments()

        for i in range(0, nr_segments):
            buf = self.__context.get_segment(i, 0)
            text = buf
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
        if Engine.__input_mode == INPUT_MODE_HIRAGANA:
            self.__preedit_ja_string.move_cursor_hiragana_length(length)
        elif Engine.__input_mode == INPUT_MODE_KATAKANA:
            self.__preedit_ja_string.move_cursor_katakana_length(length)
        elif Engine.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
            self.__preedit_ja_string.move_cursor_half_with_katakana_length(length)
        else:
            self.__preedit_ja_string.move_cursor(length)

    def __commit_nth_segment(self, commit_index, keyval, state):

        if commit_index >= len(self.__segments):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            for i in range(0, commit_index + 1):
                (seg_index, text) = self.__segments[i]
                self.commit_text(IBus.Text.new_from_string(text))

            text, cursor = self.__get_preedit()
            commit_length = 0
            for i in range(0, commit_index + 1):
                buf = self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE)
                commit_length += len(buf)
            self.__move_cursor_char_length(commit_length - cursor)
            for i in range(0, commit_length):
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
            self.__context.set_string(text)

        self.__lookup_table.clear()
        self.__lookup_table.set_cursor_visible(False)
        self.__lookup_table_visible = False
        self.update_aux_string('', IBus.AttrList(),
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
        candidate = self.__lookup_table.get_candidate(index).get_text()
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
            self.__segments[self.__cursor_pos] = n, buf
            self.__lookup_table_visible = False
            self.__invalidate()
            return True

        return False

    def __convert_to_hiragana_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)

        return self.__on_key_conv(0)

    def __convert_to_katakana_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)

        return self.__on_key_conv(1)

    def __convert_to_half_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            i, s = self.__segments[self.__cursor_pos]
            if i == -101:
                return self.__convert_segment_to_latin(-100)
            elif i == -100:
                return self.__convert_segment_to_latin(-100)
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        elif CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
            return self.__on_key_conv(4)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__on_key_conv(4)
        return self.__on_key_conv(2)

    def __convert_to_half_katakana_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        return self.__on_key_conv(2)

    def __convert_segment_to_latin(self, n):
        if self.__convert_mode == CONV_MODE_ANTHY and n in [-100, -101]:
            start = 0
            for i in range(self.__cursor_pos):
                start += len(self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE))
            end = start + len(self.__context.get_segment(self.__cursor_pos, NTH_UNCONVERTED_CANDIDATE))
            i, s = self.__segments[self.__cursor_pos]
            s2 = self.__preedit_ja_string.get_raw(start, end)
            if n == -101:
                s2 = ''.join([unichar_half_to_full(c) for c in s2])
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

    def __convert_to_wide_latin_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_latin(-101)

        return self.__on_key_conv(3)

    def __convert_to_latin_internal(self, keyval, state, mode):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            if mode == 1:
                self.__cmd_move_caret_first(keyval, state)
                self.__shrink_segment_end()
            return self.__convert_segment_to_latin(-100)

        return self.__on_key_conv(4)

    def __cmd_convert_to_hiragana(self, keyval, state):
        return self.__convert_to_hiragana_internal(keyval, state, 0)

    def __cmd_convert_to_hiragana_all(self, keyval, state):
        return self.__convert_to_hiragana_internal(keyval, state, 1)

    def __cmd_convert_to_katakana(self, keyval, state):
        return self.__convert_to_katakana_internal(keyval, state, 0)

    def __cmd_convert_to_katakana_all(self, keyval, state):
        return self.__convert_to_katakana_internal(keyval, state, 1)

    def __cmd_convert_to_half(self, keyval, state):
        return self.__convert_to_half_internal(keyval, state, 0)

    def __cmd_convert_to_half_all(self, keyval, state):
        return self.__convert_to_half_internal(keyval, state, 1)

    def __cmd_convert_to_half_katakana(self, keyval, state):
        return self.__convert_to_half_katakana_internal(keyval, state, 0)

    def __cmd_convert_to_half_katakana_all(self, keyval, state):
        return self.__convert_to_half_katakana_internal(keyval, state, 1)

    def __cmd_convert_to_wide_latin(self, keyval, state):
        return self.__convert_to_wide_latin_internal(keyval, state, 0)

    def __cmd_convert_to_wide_latin_all(self, keyval, state):
        return self.__convert_to_wide_latin_internal(keyval, state, 1)

    def __cmd_convert_to_latin(self, keyval, state):
        return self.__convert_to_latin_internal(keyval, state, 0)

    def __cmd_convert_to_latin_all(self, keyval, state):
        return self.__convert_to_latin_internal(keyval, state, 1)

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
        command = self.__prefs.get_value('common', 'dict-admin-command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_add_word(self):
        command = self.__prefs.get_value('common', 'add-word-command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_setup(self):
        if Engine.__setup_pid != 0:
            pid, state = os.waitpid(Engine.__setup_pid, os.P_NOWAIT)
            if pid != Engine.__setup_pid:
                return
            Engine.__setup_pid = 0
        setup_cmd = path.join(config.LIBEXECDIR, 'ibus-setup-anthy')
        Engine.__setup_pid = os.spawnl(os.P_NOWAIT, setup_cmd, 'ibus-setup-anthy')

    def __cmd_hiragana_for_latin_with_shift(self, keyval, state):
        self.__preedit_ja_string.set_hiragana_katakana(True)

