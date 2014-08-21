# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2014 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2014 Red Hat, Inc.
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

# for python2
from __future__ import print_function

import cairo
import sys

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo

class PropertyIcon(Gtk.StatusIcon):
    __xkb_icon_pixbufs = {}
    __xkb_icon_rgba = None

    def __init__(self, rgba):
        super(Gtk.StatusIcon, self).__init__()
        self.__xkb_icon_rgba = rgba

    def __context_render_string(self, cr, symbol, image_width, image_height):
        lwidth = 0
        lheight = 0
        desc = Pango.FontDescription.from_string('Monospace Bold 22')
        layout = PangoCairo.create_layout(cr)

        layout.set_font_description(desc)
        layout.set_text(symbol, -1)
        (lwidth, lheight) = layout.get_size()
        cr.move_to((image_width - lwidth / Pango.SCALE) / 2,
                   (image_height - lheight / Pango.SCALE) / 2)
        cr.set_source_rgba(self.__xkb_icon_rgba.red,
                           self.__xkb_icon_rgba.green,
                           self.__xkb_icon_rgba.blue,
                           self.__xkb_icon_rgba.alpha)
        PangoCairo.show_layout(cr, layout)

    def __create_icon_pixbuf_with_string(self, symbol):
        if symbol in self.__xkb_icon_pixbufs:
            return self.__xkb_icon_pixbufs[symbol]

        image = cairo.ImageSurface(cairo.FORMAT_ARGB32, 48, 48)
        cr = cairo.Context(image)
        width = image.get_width()
        height = image.get_height()

        cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        self.__context_render_string(cr, symbol, width, height)
        pixbuf = Gdk.pixbuf_get_from_surface(image, 0, 0, width, height)
        self.__xkb_icon_pixbufs[symbol] = pixbuf
        return pixbuf

    def set_from_symbol(self, symbol):
        pixbuf = self.__create_icon_pixbuf_with_string(symbol)
        self.set_from_pixbuf(pixbuf)
