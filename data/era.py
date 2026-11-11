#!/usr/bin/python3
# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2026 Takao Fujiwara <takao.fujiwara1@gmail.com>
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

from datetime import date
from os import path
import getopt
import locale
import re
import sys


_prgname = ""

class JapaneseEra(object):
    VERSION = 1
    ERA_FIRST = 2019
    HIRAGANA_ERA = 'れいわ'
    KANJI_ERA = '令和'
    KANJI_ERA_PREV = '平成'
    __S_YEAR = 0
    __M_YEAR = ''
    __narrow_to_wide_map = None
    _check = False
    _output_file = None
    _parse_file = None
    _parse_contents = None

    def __init__(self):
        if self._parse_file == None:
            print("%s.parse_args() should be called before the instance "
                  "is generated." % str(self), file=sys.stderr)
            sys.exit(1)
        self.__narrow_to_wide_map = str.maketrans('0123456789',
                                                  '０１２３４５６７８９')
        self.__S_YEAR = date.today().year
        self.__M_YEAR = str(self.__S_YEAR).translate(self.__narrow_to_wide_map)
        parse_file = open(self._parse_file)
        self._parse_contents = parse_file.read()
        parse_file.close()



    @classmethod
    def parse_args(cls)->None:

        shortopt = 'cho:v'
        longopt = ['check', 'help', 'output=', 'version']

        try:
            opts, args = getopt.gnu_getopt(sys.argv[1:], shortopt, longopt)
        except getopt.GetoptError as err:
            cls.print_help(sys.stderr, 1)

        for o, a in opts:
            if o in ('-h', '--help'):
                cls.print_help(sys.stdout)
            elif o in ('-c', '--check'):
                cls._check = True
            elif o in ('-o', '--output'):
                cls._output_file = a
            elif o in ('-v', '--version'):
                print("%s Version %d" % (_prgname, cls.VERSION))
                sys.exit(0)
            else:
                print('Unknown argument: %s' % o, file=sys.stderr)
                cls.print_help(sys.stderr, 1)

        if len(args) == 0:
            cls.print_help(sys.stderr, 1)
        cls._parse_file = args[0]


    @staticmethod
    def print_help(out, v=0)->None:
        print("%s [OPTIONS...] ERA_FILE" % _prgname, file=out)
        print("This replaces @HIRAGANA_TO_LATEST_ERA@ with latest Japanese Era "
              "in ERA_FILE",
              file=out)
        print('OPTIONS', file=out)
        print('-c, --check       Check if the latest Japanese Era in ERA_FILE.',
              file=out)
        print('-h, --help        Show this message.', file=out)
        print('-v, --version     Show version.', file=out)
        sys.exit(v)


    def run(self)->None:
        if self._check:
            self.check()
        else:
            self.update_file_with_keywords()


    def check(self)->None:
        if self._parse_contents == None:
            assert()
        pat = r'{}.*'.format(self.__M_YEAR)
        res = re.findall(pat, self._parse_contents, re.MULTILINE)
        if res:
            print(res)
        else:
            print("This year {0} is not included in {1}".format(
                    self.__M_YEAR, self._parse_file), file=sys.stderr)
            sys.exit(1)

    def update_file_with_keywords(self)->None:
        if self._parse_contents == None:
            assert()
        HIRAGANA_TO_LATEST_ERA = ''
        YEAR_TO_LATEST_ERA = ''
        s_n = 1
        s_y = self.ERA_FIRST
        while(s_y <= self.__S_YEAR):
            m_n = str(s_n).translate(self.__narrow_to_wide_map)
            m_y = str(s_y).translate(self.__narrow_to_wide_map)
            HIRAGANA_TO_LATEST_ERA = \
"""{0}{1}{2} #T35*500 {3}{4}
{5}{6} #T35*500 {7}
""".format(HIRAGANA_TO_LATEST_ERA,
           self.HIRAGANA_ERA, m_n,
           self.KANJI_ERA, s_n,
           self.HIRAGANA_ERA, m_n,
           s_y)
            YEAR_TO_LATEST_ERA = \
"""{0}{1} #T35*500 {2}{3}
""".format(YEAR_TO_LATEST_ERA,
           m_y,
           self.KANJI_ERA, s_n)
            s_n = s_n + 1
            s_y = s_y + 1
        HIRAGANA_TO_LATEST_ERA = HIRAGANA_TO_LATEST_ERA.strip()
        YEAR_TO_LATEST_ERA = YEAR_TO_LATEST_ERA.strip()
        tmp = self._parse_contents.replace(
                '@HIRAGANA_TO_REIWA@',
                HIRAGANA_TO_LATEST_ERA).replace(
                '@YEAR_TO_REIWA@',
                YEAR_TO_LATEST_ERA)
        s_y = self.ERA_FIRST
        m_y = str(s_y).translate(self.__narrow_to_wide_map)
        pat = r'({0} #T35\*500 {1}[0-9]+)\n({2} #T35\*500 {3}1)'.format(
                m_y, self.KANJI_ERA_PREV, m_y, self.KANJI_ERA)
        # The lest Era should be first.
        res = re.sub(pat, r'\2\n\1', tmp)
        if res:
            if self._output_file:
                f = open(self._output_file, mode='w')
                f.write(res)
                f.flush()
                f.close()
            else:
                print(res)
        else:
            print('Failed to find %s in %s' % (pat, self._parse_file),
                  file=sys.stderr)
            if self._output_file:
                f = open(self._output_file, mode='w')
                f.write(tmp)
                f.flush()
                f.close()
            else:
                print(tmp)


def main()->None:
    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass
    global _prgname
    _prgname = path.basename(sys.argv[0])
    JapaneseEra.parse_args()
    era = JapaneseEra()
    era.run()


if __name__ == '__main__':
    main()
