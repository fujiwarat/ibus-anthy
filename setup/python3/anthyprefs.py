# -*- coding: utf-8 -*-
# vim:set noet ts=4:
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

import sys

import _config as config
from prefs import Prefs

N_ = lambda a : a

__all__ = ['AnthyPrefs']


class AnthyPrefs(Prefs):
    _char_to_config_key = None

    def __init__(self):
        super(AnthyPrefs, self).__init__()

    def get_japanese_ordered_list(self):
        return _japanese_ordered_list

    def get_version(self):
        return config.VERSION

    # Convert gsettings key to typing sequences
    # E.g. 'largea-bracketleft' to 'A['
    def typing_from_config_key(self, gkeys):
        retval = ''
        for key in gkeys.split('-'):
            if key in _supported_gsettings_key_chars:
                retval += key
                continue
            try:
                ch = _config_key_to_char[key]
            except KeyError:
                print('Not supported key in gsettings', gkeys, file=sys.stderr)
                retval = ''
                break
            retval += ch
        return retval

    # Convert typing sequences to gsettings key.
    # E.g. 'A[' to 'largea-bracketleft'
    def typing_to_config_key(self, typing):
        retval = ''
        if self._char_to_config_key == None:
            self._char_to_config_key = {}
            for _key, _ch in list(_config_key_to_char.items()):
                self._char_to_config_key[_ch] = _key
        for ch in typing:
            if ch in _supported_gsettings_key_chars:
                if retval != '':
                    retval += '-'
                retval += ch
                continue
            try:
                key = self._char_to_config_key[ch]
            except KeyError:
                print('Not supported key in gsettings', typing, file=sys.stderr)
                retval = ''
                break
            if retval != '':
                retval += '-'
            retval += key
        return retval

    def get_value(self, section, key):
        not_sorted = super(AnthyPrefs, self).get_value(section, key)
        if section == 'shortcut' and type(not_sorted) == dict:
            retval = dict.fromkeys(_cmd_keys, [])
            retval.update(not_sorted)
            return retval
        return not_sorted


# Sad! dict.keys() doesn't return the saved order.
# locale.strcoll() also just returns the Unicode code point.
# Unicode order is wrong in Japanese large 'a' and small 'a'.
# The workaround is to save the order here...
_japanese_ordered_list = [
    'あ', 'い', 'う', 'え', 'お',
    'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ',
    'いぇ',
    'うぁ', 'うぃ', 'うぅ', 'うぇ', 'うぉ',
    'うゃ', 'うゅ', 'うょ',
    'か', 'き', 'く', 'け', 'こ',
    'ゕ', 'ゖ', 'ヵ', 'ヶ',
    'が', 'ぎ', 'ぐ', 'げ', 'ご',
    'きゃ', 'きぃ', 'きゅ', 'きぇ', 'きょ',
    'くぁ', 'くぃ', 'くぅ', 'くぇ', 'くぉ',
    'ぎゃ', 'ぎぃ', 'ぎゅ', 'ぎぇ', 'ぎょ',
    'ぐぁ', 'ぐぃ', 'ぐぅ', 'ぐぇ', 'ぐぉ',
    'さ', 'し', 'す', 'せ', 'そ',
    'ざ', 'じ', 'ず', 'ぜ', 'ぞ',
    'しゃ', 'しぃ', 'しゅ', 'しぇ', 'しょ',
    'じゃ', 'じぃ', 'じゅ', 'じぇ', 'じょ',
    'すぅぃ', 'すぇ',
    'ずぇ',
    'た', 'ち', 'つ', 'て', 'と',
    'だ', 'ぢ', 'づ', 'で', 'ど',
    'っ',
    'ちゃ', 'ちぃ', 'ちゅ', 'ちぇ', 'ちょ',
    'ぢぃ', 'ぢぇ',
    'ぢゃ', 'ぢゅ', 'ぢょ',
    'つぁ', 'つぃ', 'つぇ', 'つぉ',
    'つゃ', 'つぃぇ', 'つゅ', 'つょ',
    'づぁ', 'づぃ', 'づぇ', 'づぉ',
    'づゃ', 'づぃぇ', 'づゅ', 'づょ',
    'てぃ', 'てぇ',
    'てゃ', 'てゅ', 'てょ',
    'とぅ',
    'でぃ', 'でぇ',
    'でゃ', 'でゅ', 'でょ',
    'どぅ',
    'な', 'に', 'ぬ', 'ね', 'の',
    'にぃ', 'にぇ',
    'にゃ', 'にゅ', 'にょ',
    'は', 'ひ', 'ふ', 'へ', 'ほ',
    'ば', 'び', 'ぶ', 'べ', 'ぼ',
    'ぱ', 'ぴ', 'ぷ', 'ぺ', 'ぽ',
    'ひぃ', 'ひぇ',
    'ひゃ', 'ひゅ', 'ひょ',
    'びぃ', 'びぇ',
    'びゃ', 'びゅ', 'びょ',
    'ぴぃ', 'ぴぇ',
    'ぴゃ', 'ぴゅ', 'ぴょ',
    'ふぁ', 'ふぃ', 'ふぇ', 'ふぉ',
    'ふゃ', 'ふゅ', 'ふょ',
    'ぶぁ', 'ぶぇ', 'ぶぉ',
    'ぷぁ', 'ぷぇ', 'ぷぉ',
    'ま', 'み', 'む', 'め', 'も',
    'みぃ', 'みぇ',
    'みゃ', 'みゅ', 'みょ',
    'や', 'ゆ', 'よ',
    'ゃ', 'ゅ', 'ょ',
    'ら', 'り', 'る', 'れ', 'ろ',
    'りぃ', 'りぇ',
    'りゃ', 'りゅ', 'りょ',
    'わ', 'を', 'ん',
    'ゎ',
    'ゐ', 'ゑ',
    'ー',
    'ヴぁ', 'ヴぃ', 'ヴ', 'ヴぇ', 'ヴぉ',
    'ヴゃ', 'ヴぃぇ', 'ヴゅ', 'ヴょ',
]

# http://git.gnome.org/browse/glib/tree/gio/glib-compile-schemas.c#n765
# gsettings supports keys named by "abcdefghijklmnopqrstuvwxyz0123456789-"
# and ibus-anthy uses '-' as the delimiter.
_supported_gsettings_key_chars = "abcdefghijklmnopqrstuvwxyz0123456789"

_config_key_to_char = {
    # no modifiers keys
    'minus'         : '-',
    'asciicircum'   : '^',
    'at'            : '@',
    'bracketleft'   : '[',
    'semicolon'     : ';',
    'colon'         : ':',
    'bracketright'  : ']',
    'comma'         : ',',
    'period'        : '.',
    'slash'         : '/',
    'backslash'     : '\\',

    # shift modifiered keys
    'exclam'        : '!',
    'quotedbl'      : '"',
    'numbersign'    : '#',
    'dollar'        : '$',
    'percent'       : '%',
    'ampersand'     : '&',
    'apostrophe'    : '\'',
    'parenleft'     : '(',
    'parenright'    : ')',
    'asciitilde'    : '~',
    'equal'         : '=',
    'bar'           : '|',

    'largeq'        : 'Q',
    'largew'        : 'W',
    'largee'        : 'E',
    'larger'        : 'R',
    'larget'        : 'T',
    'largey'        : 'Y',
    'largeu'        : 'U',
    'largei'        : 'I',
    'largeo'        : 'O',
    'largep'        : 'P',
    'grave'         : '`',

    'braceleft'     : '{',

    'largea'        : 'A',
    'larges'        : 'S',
    'larged'        : 'D',
    'largef'        : 'F',
    'largeg'        : 'G',
    'largeh'        : 'H',
    'largej'        : 'J',
    'largek'        : 'K',
    'largel'        : 'L',
    'plus'          : '+',
    'asterisk'      : '*',

    'braceright'    : '}',

    'largez'        : 'Z',
    'largex'        : 'X',
    'largec'        : 'C',
    'largev'        : 'V',
    'largeb'        : 'B',
    'largen'        : 'N',
    'largem'        : 'M',
    'less'          : '<',
    'greater'       : '>',

    'question'      : '?',
    'underscore'    : '_',

    'yen'           : '¥',
}

_cmd_keys = [
    'on_off',
    'circle_input_mode',
    'circle_kana_mode',
    'circle_typing_method',
    'circle_dict_method',
    'latin_mode',
    'wide_latin_mode',
    'hiragana_mode',
    'katakana_mode',
    'half_katakana_mode',
#    'cancel_pseudo_ascii_mode_key',

    'hiragana_for_latin_with_shift',

    'insert_space',
    'insert_alternate_space',
    'insert_half_space',
    'insert_wide_space',
    'backspace',
    'delete',
    'commit',
    'convert',
    'predict',
    'cancel',
    'cancel_all',
    'escape_to_latin',
    'reconvert',
#    'do_nothing',

    'select_first_candidate',
    'select_last_candidate',
    'select_next_candidate',
    'select_prev_candidate',
    'candidates_page_up',
    'candidates_page_down',

    'move_caret_first',
    'move_caret_last',
    'move_caret_forward',
    'move_caret_backward',

    'select_first_segment',
    'select_last_segment',
    'select_next_segment',
    'select_prev_segment',
    'shrink_segment',
    'expand_segment',
    'commit_first_segment',
    'commit_selected_segment',

    'select_candidates_1',
    'select_candidates_2',
    'select_candidates_3',
    'select_candidates_4',
    'select_candidates_5',
    'select_candidates_6',
    'select_candidates_7',
    'select_candidates_8',
    'select_candidates_9',
    'select_candidates_0',

    'convert_to_char_type_forward',
    'convert_to_char_type_backward',
    'convert_to_hiragana',
    'convert_to_katakana',
    'convert_to_half',
    'convert_to_half_katakana',
    'convert_to_wide_latin',
    'convert_to_latin',
    'convert_to_hiragana_all',
    'convert_to_katakana_all',
    'convert_to_half_all',
    'convert_to_half_katakana_all',
    'convert_to_wide_latin_all',
    'convert_to_latin_all',

    'dict_admin',
    'add_word',

    'start_setup',
]

_dummy_translatable_strings = [
    N_('General'),
    N_('Zip Code Conversion'),
    N_('Symbol'),
    N_('Old Character Style'),
    N_('Era'),
    N_('Emoji'),
]
