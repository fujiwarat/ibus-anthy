# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2014 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2014 Red Hat, Inc.
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

from tables import *

_half_full_table = [
    (0x0020, 0x3000, 1),
    (0x0021, 0xFF01, 0x5E),
]

def _h_to_f(c):
    code = ord (c)
    for half, full, size in _half_full_table:
        if code >= half and code < half + size:
            return chr(full + code - half)
    return c

def unichar_half_to_full(c):
    tdl = {'"': '\u201d', "'": '\u2019', '`': '\u2018'}
    return tdl[c] if c in tdl else _h_to_f(c)

class Segment(object):
    def __init__(self, enchars='', jachars=''):
        self._enchars = enchars
        self._jachars = jachars

    def append(self, enchar):
        raise NotImplementedError('append() is not implemented')

    def prepend(self, enchar):
        raise NotImplementedError('prepend() is not implemented')

    def pop(self, index=-1):
        raise NotImplementedError('pop() is not implemented')

    def is_finished(self):
        raise NotImplementedError('is_finised() is not implemented')

    def set_enchars(self, enchars):
        self.enchars = enchars

    def get_enchars(self):
        return self._enchars

    def set_jachars(self, jachars):
        self._jachars = jachars

    def get_jachars(self):
        return self._jachars

    def to_hiragana(self):
        if self._jachars:
            return self._jachars
        return self._enchars

    def to_katakana(self):
        if self._jachars:
            return ''.join([hiragana_katakana_table.get(c, (c, c, c))[0] for c in self._jachars])
        return self._enchars

    def to_half_width_katakana(self):
        if self._jachars:
            return ''.join([hiragana_katakana_table.get(c, (c, c, c))[1] for c in self._jachars])
        return self._enchars

    def to_latin(self):
        return self._enchars

    def to_wide_latin(self):
        return ''.join(map(unichar_half_to_full, self._enchars))

    def is_empty(self):
        if self._enchars or self._jachars:
            return False
        return True
