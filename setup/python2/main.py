# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
# Copyright (c) 2010-2021 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2019 Red Hat, Inc.
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

from os import environ, getuid, path
import os, sys
import locale
import xml.dom.minidom
import gettext
from gettext import dgettext

from gi import require_version as gi_require_version
gi_require_version('Gio', '2.0')
gi_require_version('GLib', '2.0')
gi_require_version('Gtk', '3.0')
gi_require_version('Gdk', '3.0')
gi_require_version('GdkX11', '3.0')
gi_require_version('Pango', '1.0')
gi_require_version('IBus', '1.0')

from gi.repository import Gio
from gi.repository import GLib

# set_prgname before importing other modules to show the name in warning
# messages when import modules are failed. E.g. Gtk.
GLib.set_prgname('ibus-setup-anthy')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import Pango
from gi.repository import IBus

import _config as config
from anthyprefs import AnthyPrefs

DOMAINNAME = 'ibus-anthy'
_ = lambda a : dgettext('ibus-anthy', a)

def l_to_s(l):
    return str(sorted([str(s) for s in l])).replace('\'', '')

def s_to_l(s):
    return [] if s == '[]' else s[1:-1].replace(' ', '').split(',')


class AnthySetup(object):
    def __init__(self):
        # Python's locale module doesn't provide all methods on some
        # operating systems like FreeBSD
        try:
            locale.bindtextdomain(DOMAINNAME, config.LOCALEDIR)
            locale.bind_textdomain_codeset(DOMAINNAME, 'UTF-8')
        except AttributeError:
            pass
        gettext.bindtextdomain(DOMAINNAME, config.LOCALEDIR)
        gettext.bind_textdomain_codeset(DOMAINNAME, 'UTF-8')

        self.__prefs =  AnthyPrefs()

        builder_file = path.join(path.dirname(__file__), 'setup.ui')
        self.__builder = builder = Gtk.Builder()
        builder.set_translation_domain(DOMAINNAME)
        builder.add_from_file(builder_file)

        toplevel = builder.get_object('main')
        parent_xid = 0
        parent_wmname = None
        parent_wmclass = None

        try:
            parent_xid = int(environ['IBUS_SETUP_XID'])
            if parent_xid != 0:
                parent_wmname = 'ibus-setup'
                parent_wmclass = 'Ibus-setup'
        except:
            pass

        try:
            if parent_xid == 0:
                parent_xid = int(environ['GNOME_CONTROL_CENTER_XID'])
                if parent_xid != 0:
                    parent_wmname = 'gnome-conrol-center'
                    parent_wmclass = 'Gnome-conrol-center'
        except:
            pass

        if parent_xid != 0:
            def set_transient(obj, pspec):
                window = toplevel.get_window()
                if window == None:
                    return
                parent_window = GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(),
                                                                         parent_xid)
                if parent_window != None:
                    window.set_transient_for(parent_window)
            toplevel.set_wmclass(parent_wmname, parent_wmclass)
            toplevel.set_modal(True)
            toplevel.set_type_hint(Gdk.WindowTypeHint.DIALOG)
            toplevel.connect('notify::window', set_transient)

        toplevel.show()
        self.__init_bus_connected()

    def __init_bus_connected(self):
        builder = self.__builder
        prefs = self.__prefs

        self.__thumb_kb_layout_mode = None
        self.__thumb_kb_layout = None
        self.__japanese_ordered_dict = {}

        # glade 'icon_name' property has a custom scaling and it seems
        # to be difficult to show the complicated small icon in metacity.
        # This can add the pixbuf without scaling.
        anthydir = path.dirname(path.dirname(__file__))
        if not anthydir:
            anthydir = '/usr/share/ibus-anthy'
        icon_path = path.join(anthydir, 'icons', 'ibus-anthy.png')
        if path.exists(icon_path):
            builder.get_object('main').set_icon_from_file(icon_path)
        else:
            icon_path = 'ibus-anthy'
            builder.get_object('main').set_icon_name(icon_path)

        for name in ['input-mode', 'typing-method', 'conversion-segment-mode',
                     'period-style', 'symbol-style', 'ten-key-mode',
                     'behavior-on-focus-out', 'behavior-on-period',
                     'half-width-symbol', 'half-width-number', 'half-width-space',
                     'latin-with-shift',
                     'thumb:keyboard-layout-mode', 'thumb:keyboard-layout',
                     'thumb:fmv-extension', 'thumb:handakuten']:
            section, key = self.__get_section_key(name)
            prefs.bind(section, key,
                       builder.get_object(name),
                       'active',
                       Gio.SettingsBindFlags.DEFAULT)

        prefs.bind('thumb', 'keyboard-layout-mode',
                   builder.get_object('thumb:keyboard-layout'),
                   'sensitive',
                   Gio.SettingsBindFlags.INVERT_BOOLEAN)

        tv = builder.get_object('menu-visible:treeview')
        ls = Gtk.ListStore(str, bool, str)
        tv.set_model(ls)

        column = Gtk.TreeViewColumn(' ')
        renderer = Gtk.CellRendererToggle()
        renderer.set_radio(False)
        renderer.connect('toggled', self.__renderer_toggled_cb, ls)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer,
                                  self.__toggle_menu_visible_cell_cb,
                                  1)
        tv.append_column(column)

        column = Gtk.TreeViewColumn(_("Menu label"))
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer,
                                  self.__text_menu_visible_cell_cb,
                                  2)
        tv.append_column(column)

        self.__append_menus_in_model()

        l = ['default', 'atok', 'wnn']
        s_type = prefs.get_value('common', 'shortcut-type')
        s_type = s_type if s_type in l else 'default'
        builder.get_object('shortcut-type').set_active(l.index(s_type))

        prefs.bind('common', 'page-size',
                   builder.get_object('page-size').get_adjustment(),
                   'value',
                   Gio.SettingsBindFlags.DEFAULT)

        tv = builder.get_object('shortcut')
        tv.append_column(Gtk.TreeViewColumn(_("Command"),
                                             Gtk.CellRendererText(), text=0))
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        tv.append_column(Gtk.TreeViewColumn(_("Shortcut"),
                                             renderer, text=1))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 0)
        ls = Gtk.ListStore(str, str)
        shortcuts = self.__prefs.get_value('shortcut', s_type)
        for k in shortcuts.keys():
            ls.append([k, l_to_s(shortcuts[k])])
        tv.set_model(ls)

        self.__keymap = None
        GLib.idle_add(self.__update_keymap_label,
                      priority = GLib.PRIORITY_LOW)

        self.__thumb_kb_layout_mode = builder.get_object('thumb:keyboard-layout-mode')
        self.__thumb_kb_layout = builder.get_object('thumb:keyboard-layout')
        self.__set_thumb_kb_label()

        for name in ['thumb:ls', 'thumb:rs']:
            section, key = self.__get_section_key(name)
            builder.get_object(name).set_text(prefs.get_value(section, key))

        tv = builder.get_object('es:treeview')
        tv.append_column(Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=0))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 1)
        tv.set_model(Gtk.ListStore(str))

        key = 'dict-admin-command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry-edit-dict-command'
        builder.get_object(name).set_text(cli)
        key = 'add-word-command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry-add-word-command'
        builder.get_object(name).set_text(cli)

        tv = builder.get_object('dict:view')

        column = Gtk.TreeViewColumn(' ')
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__text_cell_data_cb, 1)
        tv.append_column(column)

        column = Gtk.TreeViewColumn(_("Description"))
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__text_cell_data_cb, 2)
        column.set_expand(True)
        tv.append_column(column)

        # Translators: "Embd" is an abbreviation of "embedded".
        column = Gtk.TreeViewColumn(_("Embd"))
        renderer = Gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 3)
        tv.append_column(column)

        # Translators: "Sgl" is an abbreviation of "single".
        column = Gtk.TreeViewColumn(_("Sgl"))
        renderer = Gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 4)
        tv.append_column(column)

        '''
        Unfortunately reverse conversion is too slow.
        # Translators: "Rev" is an abbreviation of "reverse".
        column = Gtk.TreeViewColumn(_("Rev"))
        renderer = Gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 5)
        tv.append_column(column)
        '''

        ls = Gtk.ListStore(str, str, str, bool, bool, bool)
        tv.set_model(ls)
        self.__append_dicts_in_model()

        self.__init_japanese_sort()
        self.__init_about_vbox(icon_path)

        builder.connect_signals(self)

    def __init_japanese_sort(self):
        japanese_ordered_dict = {}
        japanese_ordered_list = self.__prefs.get_japanese_ordered_list()
        for index, c in enumerate(japanese_ordered_list):
            japanese_ordered_dict[c] = index
        self.__japanese_ordered_dict = japanese_ordered_dict;

    def __init_about_vbox(self, icon_path):
        about_dialog = self.__builder.get_object('about_dialog')
        about_vbox = self.__builder.get_object('about_vbox')
        about_dialog.set_version(self.__prefs.get_version())
        if icon_path != None:
            if icon_path[0] == '/':
                image = Gtk.Image.new_from_file(icon_path)
                about_dialog.set_logo(image.get_pixbuf())
            else:
                icon_theme = Gtk.IconTheme.get_default()
                try:
                    pixbuf = icon_theme.load_icon(icon_path, 48, 0)
                    about_dialog.set_logo(pixbuf)
                except Exception, err:
                    print >> sys.stderr, 'Not found icon', str(err)
                    print >> sys.stderr, 'Need to run gtk-update-icon-cache'
        content_area = about_dialog.get_content_area()
        list = content_area.get_children()
        vbox = list[0]
        for w in vbox.get_children():
            old_parent = w.props.parent
            w.unparent()
            w.emit('parent-set', old_parent)
            about_vbox.pack_start(w, False, False, 0)

    def __get_userhome(self):
        if 'HOME' not in environ:
            import pwd
            userhome = pwd.getpwuid(getuid()).pw_dir
        else:
            userhome = environ['HOME']
        userhome = userhome.rstrip('/')
        return userhome

    def __get_section_key(self, name):
        i = name.find(':')
        if i > 0:
            section = name[:i]
            key = name[i + 1:]
        else:
            section = 'common'
            key = name
        return (section, key)

    def __run_message_dialog(self, message, type=Gtk.MessageType.INFO):
        dlg = Gtk.MessageDialog(
                transient_for=self.__builder.get_object('main'),
                message_type=type,
                buttons=Gtk.ButtonsType.OK,
                text=message)
        dlg.run()
        dlg.destroy()

    def _get_shortcut_sec(self):
        l = ['default', 'atok', 'wnn']
        iter = self.__builder.get_object('shortcut-type').get_active_iter()
        model = self.__builder.get_object('shortcut-type').get_model()
        s_type = model[iter][0].lower()
        return 'shortcut/' + (s_type if s_type in l else 'default')

    def __get_shortcut_group(self):
        l = ['default', 'atok', 'wnn']
        iter = self.__builder.get_object('shortcut-type').get_active_iter()
        model = self.__builder.get_object('shortcut-type').get_model()
        s_type = model[iter][0].lower()
        return s_type if s_type in l else 'default'

    def __japanese_tuple_sort(self, a, b):
        if a[1] == b[1]:
            return cmp(a[0], b[0])
        elif a[1] in self.__japanese_ordered_dict and \
            b[1] in self.__japanese_ordered_dict:
            return self.__japanese_ordered_dict[a[1]] - \
                self.__japanese_ordered_dict[b[1]]
        elif a[1] not in self.__japanese_ordered_dict and \
            b[1] in self.__japanese_ordered_dict:
            return 1
        elif a[1] in self.__japanese_ordered_dict and \
            b[1] not in self.__japanese_ordered_dict:
            return -1
        else:
            return cmp(a[1], b[1])

    def __japanese_thumb_sort(self, a, b):
        return cmp(a[0], b[0])

    def __renderer_toggled_cb(self, renderer, path, model):
        prefs = self.__prefs
        enabled = not model[path][1]
        model[path][1] = enabled
        key = model[path][0]
        prefs.set_value('common', key, enabled)

    def __toggle_menu_visible_cell_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('menu-visible:treeview').get_model()
        active = l.get_value(iter, id)
        renderer.set_property('active', active)

    def __text_menu_visible_cell_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('menu-visible:treeview').get_model()
        text = l.get_value(iter, id)
        renderer.set_property('text', text)

    def __append_menus_in_model(self):
        prefs = self.__prefs
        l = self.__builder.get_object('menu-visible:treeview').get_model()
        l.append(['show-input-mode',
                  prefs.get_value('common', 'show-input-mode'),
                  _("Input mode")])
        l.append(['show-typing-method',
                  prefs.get_value('common', 'show-typing-method'),
                  _("Typing method")])
        l.append(['show-segment-mode',
                  prefs.get_value('common', 'show-segment-mode'),
                  _("Segment mode")])
        l.append(['show-dict-mode',
                  prefs.get_value('common', 'show-dict-mode'),
                  _("Dictionary mode")])
        l.append(['show-dict-config',
                  prefs.get_value('common', 'show-dict-config'),
                  _("Dictionary - Anthy")])
        l.append(['show-preferences',
                  prefs.get_value('common', 'show-preferences'),
                  _("Preferences - Anthy")])

    def __get_romaji_treeview_custom_key_table(self, method):
        prefs = self.__prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section = 'romaji-typing-rule'
        keymap = prefs.get_value(section, 'list')[method]
        for key in keymap.keys():
            value = keymap[key]
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = value
        for key, value in sorted(rule.items(), \
            cmp = self.__japanese_tuple_sort):
            ls.append(['romaji', key, value])
        tv.set_model(None)
        tv.append_column(Gtk.TreeViewColumn(_(_("Input Chars")),
                                            Gtk.CellRendererText(), text=1))
        tv.append_column(Gtk.TreeViewColumn(_(_("Output Chars")),
                                            Gtk.CellRendererText(), text=2))
        tv.set_model(ls)
        return tv

    def __get_kana_treeview_custom_key_table(self, method):
        prefs = self.__prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section = 'kana-typing-rule'
        keymap = prefs.get_value(section, 'list')[method]
        for key in keymap.keys():
            value = keymap[key]
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = value
        for key, value in sorted(rule.items(), \
            cmp = self.__japanese_tuple_sort):
            ls.append(['kana', key, value])
        tv.set_model(None)
        tv.append_column(Gtk.TreeViewColumn(_(_("Input Chars")),
                                            Gtk.CellRendererText(), text=1))
        tv.append_column(Gtk.TreeViewColumn(_(_("Output Chars")),
                                            Gtk.CellRendererText(), text=2))
        tv.set_model(ls)
        return tv

    def __get_thumb_treeview_custom_key_table(self, method):
        prefs = self.__prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section = 'thumb-typing-rule'
        keymap = prefs.get_value(section, 'list')[method]
        for key in keymap.keys():
            value = keymap[key]
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and len(value) == 3 and \
                ((value[0] != None and value[0] != '') or \
                 (value[1] != None and value[1] != '') or \
                 (value[2] != None and value[2] != '')):
                rule[ch] = {}
                rule[ch][0] = value[0]
                rule[ch][1] = value[1]
                rule[ch][2] = value[2]
        for key, value in sorted(rule.items(), \
            cmp = self.__japanese_thumb_sort):
            ls.append(['thumb', key, value[0], value[2], value[1]])
        tv.set_model(None)
        tv.append_column(Gtk.TreeViewColumn(_(_("Input")),
                                            Gtk.CellRendererText(), text=1))
        tv.append_column(Gtk.TreeViewColumn(_(_("Single")),
                                            Gtk.CellRendererText(), text=2))
        tv.append_column(Gtk.TreeViewColumn(_(_("Left")),
                                            Gtk.CellRendererText(), text=3))
        tv.append_column(Gtk.TreeViewColumn(_(_("Right")),
                                            Gtk.CellRendererText(), text=4))
        tv.set_model(ls)
        return tv

    def __show_dialog_custom_key_table_extention(self, mode):
        hbox_combo = self.__builder.get_object('hbox_for_combobox_custom_key_table')
        label_left = self.__builder.get_object('label_left_thumb_shift_custom_key')
        entry_left = self.__builder.get_object('entry_left_thumb_shift_custom_key')
        label_right = self.__builder.get_object('label_right_thumb_shift_custom_key')
        entry_right = self.__builder.get_object('entry_right_thumb_shift_custom_key')
        if mode == 'thumb':
            hbox_combo.show()
            label_left.show()
            entry_left.show()
            label_right.show()
            entry_right.show()
        elif mode == 'kana':
            hbox_combo.show()
            label_left.hide()
            entry_left.hide()
            label_right.hide()
            entry_right.hide()
        else:
            hbox_combo.hide()
            label_left.hide()
            entry_left.hide()
            label_right.hide()
            entry_right.hide()

    def __connect_dialog_custom_key_table_buttons(self, mode):
        tv = self.__builder.get_object('treeview_custom_key_table')
        tv.get_selection().connect_after('changed',
                                         self.on_selection_custom_key_table_changed, 0)
        entry = self.__builder.get_object('entry_input_custom_key')
        entry.connect('changed', self.on_entry_custom_key_changed, mode)
        entry = self.__builder.get_object('entry_output_custom_key')
        entry.connect('changed', self.on_entry_custom_key_changed, mode)
        entry = self.__builder.get_object('entry_left_thumb_shift_custom_key')
        entry.connect('changed', self.on_entry_custom_key_changed, mode)
        entry = self.__builder.get_object('entry_right_thumb_shift_custom_key')
        entry.connect('changed', self.on_entry_custom_key_changed, mode)
        button = self.__builder.get_object('button_add_custom_key')
        button.set_sensitive(False)
        button.connect('clicked', self.on_btn_add_custom_key, mode)
        button = self.__builder.get_object('button_remove_custom_key')
        button.set_sensitive(False)
        button.connect('clicked', self.on_btn_remove_custom_key, tv)

    def __disconnect_dialog_custom_key_table_buttons(self):
        tv = self.__builder.get_object('treeview_custom_key_table')
        combobox = self.__builder.get_object('combobox_custom_key_table')
        if tv != None:
            for column in tv.get_columns():
                tv.remove_column(column)
            for child in tv.get_children():
                tv.remove(child)
            entry = self.__builder.get_object('entry_input_custom_key')
            entry.disconnect_by_func(self.on_entry_custom_key_changed)
            entry.set_text('')
            entry = self.__builder.get_object('entry_output_custom_key')
            entry.disconnect_by_func(self.on_entry_custom_key_changed)
            entry.set_text('')
            entry = self.__builder.get_object('entry_left_thumb_shift_custom_key')
            entry.disconnect_by_func(self.on_entry_custom_key_changed)
            entry = self.__builder.get_object('entry_right_thumb_shift_custom_key')
            entry.disconnect_by_func(self.on_entry_custom_key_changed)
            button = self.__builder.get_object('button_add_custom_key')
            button.disconnect_by_func(self.on_btn_add_custom_key)
            button = self.__builder.get_object('button_remove_custom_key')
            button.disconnect_by_func(self.on_btn_remove_custom_key)
        combobox.clear()
        combobox.disconnect_by_func(self.on_cb_custom_key_table_changed)

    def __run_dialog_custom_key_table(self, widget, mode):
        prefs = self.__prefs
        dlg = self.__builder.get_object('dialog_custom_key_table')
        dlg.set_transient_for(widget.get_toplevel())
        label = self.__builder.get_object('label_custom_key_table')
        label_output = self.__builder.get_object('label_output_custom_key')
        list_labels = []
        if mode == 'romaji':
            dlg.set_title(_("Customize Romaji Key Table"))
            label.set_label(_("_Romaji Key Table:"))
            label_output.set_label(_("_Output Chars"))
            list_labels = [['default', _("Default")]]
            self.__show_dialog_custom_key_table_extention(mode)
        elif mode == 'kana':
            dlg.set_title(_("Customize Kana Key Table"))
            label.set_label(_("_Kana Key Table:"))
            label_output.set_label(_("_Output Chars"))
            list_labels = [['jp', _("Japanese Keyboard Layout")],
                           ['us', _("U.S. Keyboard Layout")]]
            self.__show_dialog_custom_key_table_extention(mode)
        elif mode == 'thumb':
            dlg.set_title(_("Customize Thumb Shift Key Table"))
            label.set_label(_("_Thumb Shift Key Table:"))
            label_output.set_label(_("Single _Output Chars"))
            list_labels = [['base', _("Base")],
                           ['nicola-j-table', _("NICOLA-J key extension")],
                           ['nicola-a-table', _("NICOLA-A key extension")],
                           ['nicola-f-table', _("NICOLA-F key extension")],
                           ['kb231-j-fmv-table', _("FMV KB231-J key extension")],
                           ['kb231-a-fmv-table', _("FMV KB231-A key extension")],
                           ['kb231-f-fmv-table', _("FMV KB231-F key extension")],
                           ['kb611-j-fmv-table', _("FMV KB611-J key extension")],
                           ['kb611-a-fmv-table', _("FMV KB611-A key extension")],
                           ['kb611-f-fmv-table', _("FMV KB611-F key extension")],
                          ]
            self.__show_dialog_custom_key_table_extention(mode)
        ls = Gtk.ListStore(str, str)
        for s in list_labels:
            ls.append([s[1], s[0]])
        renderer = Gtk.CellRendererText()
        combobox = self.__builder.get_object('combobox_custom_key_table')
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, 'text', 0)
        combobox.set_model(ls)

        tv = None
        if mode == 'romaji':
            method = prefs.get_value('romaji-typing-rule', 'method')
            if method == None:
                method = 'default'
            tv = self.__get_romaji_treeview_custom_key_table(method)
        if mode == 'kana':
            method = prefs.get_value('kana-typing-rule', 'method')
            if method == None:
                method = 'jp'
            tv = self.__get_kana_treeview_custom_key_table(method)
        if mode == 'thumb':
            method = prefs.get_value('thumb-typing-rule', 'method')
            if method == None:
                method = 'base'
            tv = self.__get_thumb_treeview_custom_key_table(method)

        self.__connect_dialog_custom_key_table_buttons(mode)

        id = 0
        # thumb uses all tables so the default is always 0.
        if mode != 'thumb':
            id = -1
            for index, labels in enumerate(list_labels):
                if labels[0] == method:
                    id = index
                    break
            if id == -1:
                ls.append([method, method])
                combobox.set_model(ls)
                id = len(list_labels)
        combobox.set_active(id)
        combobox.connect('changed', self.on_cb_custom_key_table_changed, mode)

        id = dlg.run()
        dlg.hide()

        self.__disconnect_dialog_custom_key_table_buttons()

    def __set_thumb_kb_label(self):
        if self.__thumb_kb_layout_mode == None or \
           self.__thumb_kb_layout == None:
            return
        section, key = self.__get_section_key(
            Gtk.Buildable.get_name(self.__thumb_kb_layout_mode))
        layout_mode = self.__prefs.get_value(section, key)
        if layout_mode:
            self.__thumb_kb_layout.set_sensitive(False)
        else:
            self.__thumb_kb_layout.set_sensitive(True)

    def __get_dict_cli_from_list(self, cli_list):
            cli_str = cli_list[0]
            if len(cli_list) <= 2:
                return cli_str
            cli_str = cli_str + ' ' + ' '.join(cli_list[2:])
            return cli_str

    def __get_quoted_id(self, file):
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

    def __get_dict_file_from_id(self, selected_id):
        files = self.__prefs.get_value('dict', 'files')
        return files.get(selected_id, None)

    def __is_system_dict_file_from_id(self, selected_id):
        prefs = self.__prefs
        dict_item = prefs.get_value('dict', 'list')[selected_id]
        return dict_item.is_system

    def __append_dict_id_in_model(self, id):
        prefs = self.__prefs
        section = 'dict/file/' + id
        dicts = prefs.get_value('dict', 'list')
        dict_item = dicts[id]
        short_label = dict_item.short_label
        long_label = dict_item.long_label
        embed = dict_item.embed
        single = dict_item.single
        reverse = dict_item.reverse
        if dict_item.is_system:
            long_label = _(long_label)
        l = self.__builder.get_object('dict:view').get_model()
        l.append([id, short_label, long_label, embed, single, reverse])

    def __append_dicts_in_model(self):
        prefs = self.__prefs
        order = prefs.get_value('dict', 'order')
        dict_files = prefs.get_value('dict', 'files')
        if len(order) == 0:
            order = list(dict_files.keys())
        for id in order:
            if id == 'embedded':
                continue
            files = dict_files[id]
            for file in files:
                if not path.exists(file):
                    continue
            self.__append_dict_id_in_model(id)

    def __append_user_dict_from_dialog(self, file, id, new):
        files_dict = self.__prefs.get_value('dict', 'files')

        if new:
            files = []
            for v in files_dict.values():
                for f in v:
                    files.append(f)
            if file in files:
                self.__run_message_dialog(_("Your choosed file has already been added: ") + file,
                                          Gtk.MessageType.ERROR)
                return
            if not path.exists(file):
                self.__run_message_dialog(_("The file you have chosen does not exist: ") + file,
                                          Gtk.MessageType.ERROR)
                return
            if path.isdir(file):
                self.__run_message_dialog(_("Your choosed file is a directory: " + file),
                                          Gtk.MessageType.ERROR)
                return
            if file.startswith(self.__get_userhome() + '/.anthy'):
                self.__run_message_dialog(_("You cannot add dictionaries in the anthy private directory: " + file),
                                          Gtk.MessageType.ERROR)
                return
        else:
            file = files_dict[id][0]

        if new:
            id = self.__get_quoted_id(file)
        if id == None or id == '':
            self.__run_message_dialog(_("Your file path is not good: ") + file,
                                      Gtk.MessageType.ERROR)
            return

        single = self.__builder.get_object('dict:single').get_active()
        embed = self.__builder.get_object('dict:embed').get_active()
        reverse = self.__builder.get_object('dict:reverse').get_active()
        short_label = self.__builder.get_object('dict:short_entry').get_text()
        if len(unicode(short_label, 'utf-8')) > 1:
            short_label = unicode(short_label, 'utf-8')[0].encode('utf-8')
        long_label = self.__builder.get_object('dict:long_entry').get_text()

        if new:
            order = self.__prefs.get_value('dict', 'order')
            if len(order) == 0:
                order = list(self.__prefs.get_value('dict', 'files').keys())
            order.append(id)
            self.__prefs.set_value('dict', 'order', order)
            self.__prefs.set_list_item('dict', 'files', id, [file])

        filename = file
        if filename.find('/') >=0:
            filename = filename[filename.rindex('/') + 1:]
        if filename.find('.') >=0:
            filname = filename[:filename.rindex('.')]
        if short_label == None or short_label == '':
                short_label = filename[0]
        if long_label == None or long_label == '':
                long_label = filename
        self.__update_dict_values(new, id, short_label, long_label, embed, single, reverse)
        files = []

    def __init_dict_chooser_dialog(self):
        self.__builder.get_object('dict:single').set_active(True)
        self.__builder.get_object('dict:embed').set_active(False)
        self.__builder.get_object('dict:reverse').set_active(False)
        short_entry = self.__builder.get_object('dict:short_entry')
        short_entry.set_text('')
        short_entry.set_editable(True)
        long_entry = self.__builder.get_object('dict:long_entry')
        long_entry.set_text('')
        long_entry.set_editable(True)

    def __get_selected_dict_id(self):
        l, it = self.__builder.get_object('dict:view').get_selection().get_selected()

        if not it:
            return None
        return l.get_value(it, 0)

    def __set_selected_dict_to_dialog(self):
        selected_id = self.__get_selected_dict_id()
        if selected_id == None:
            return None

        dict_item = self.__prefs.get_value('dict', 'list')[selected_id]
        short_label = dict_item.short_label
        long_label = dict_item.long_label
        embed = dict_item.embed
        single = dict_item.single
        reverse = dict_item.reverse
        is_system_dict = dict_item.is_system

        if len(self.__prefs.unicode(short_label)) > 1:
            short_label = self.__prefs.unicode(short_label)[0].encode('utf-8')
        self.__builder.get_object('dict:single').set_active(single)
        self.__builder.get_object('dict:embed').set_active(embed)
        self.__builder.get_object('dict:reverse').set_active(reverse)
        short_entry = self.__builder.get_object('dict:short_entry')
        short_entry.set_text(short_label)
        long_entry = self.__builder.get_object('dict:long_entry')
        if is_system_dict:
            short_entry.set_editable(False)
            long_entry.set_text(_(long_label))
            long_entry.set_editable(False)
        else:
            short_entry.set_editable(True)
            long_entry.set_text(long_label)
            long_entry.set_editable(True)

        return selected_id

    def __update_dict_values(self, new, id, short_label, long_label, embed, single, reverse):
        prefs = self.__prefs

        if new:
            dict_item = prefs.get_value('dict', 'template')
            dict_item.id = id
            dict_item.short_label = short_label
            dict_item.long_label = long_label
            dict_item.embed = embed
            dict_item.single = single
            dict_item.reverse = reverse
            l = self.__builder.get_object('dict:view').get_model()
            l.append([id, short_label, long_label, embed, single, reverse])
        else:
            dict_item = prefs.get_value('dict', 'list')[id]
            if not dict_item.is_system:
                dict_item.short_label = short_label
                dict_item.long_label = long_label
            dict_item.embed = embed
            dict_item.single = single
            dict_item.reverse = reverse
            l, i = self.__builder.get_object('dict:view').get_selection().get_selected()
            if i :
                l[i] = [id, short_label, long_label, embed, single, reverse]

        prefs.set_list_item('dict', 'list', id, dict_item)

    def __text_cell_data_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('dict:view').get_model()
        text = l.get_value(iter, id)
        renderer.set_property('text', text)

    def __toggle_cell_data_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('dict:view').get_model()
        active = l.get_value(iter, id)
        renderer.set_property('active', active)

    def __resync_engine_file(self):
        user_config = path.join(self.__get_userhome(), '.config',
                                'ibus-anthy', 'engines.xml')
        system_config = path.join(config.PKGDATADIR, 'engine', 'default.xml')
        if not path.exists(user_config):
            return
        if not path.exists(system_config):
            os.unlink(user_config)
            return

        # path.getmtime depends on the build time rather than install time.
        def __get_engine_file_version(engine_file):
            version_str = ''
            dom = xml.dom.minidom.parse(engine_file)
            elements = dom.getElementsByTagName('version')
            nodes = []
            if len(elements) > 0:
                nodes = elements[0].childNodes
            if len(nodes) > 0:
                version_str = nodes[0].data
            if type(version_str) == unicode:
                version_str = str(version_str)
            if version_str != '':
                version_str = version_str.strip()
            return version_str

        user_config_version = __get_engine_file_version(user_config)
        system_config_version = __get_engine_file_version(system_config)
        if system_config_version > user_config_version:
            import shutil
            shutil.copyfile(system_config, user_config)

    def __get_engine_file(self):
        user_config = path.join(self.__get_userhome(), '.config',
                                'ibus-anthy', 'engines.xml')
        system_config = path.join(config.PKGDATADIR, 'engine', 'default.xml')
        engine_file = None
        for f in [user_config, system_config]:
            if path.exists(f):
                engine_file = f
                break
        if engine_file == None:
            self.__run_message_dialog(_("The engine xml file does not exist: ") + system_config,
                                      Gtk.MessageType.ERROR)
            return None
        return engine_file

    def __get_keymap(self):
        keymap = ''
        layout = ''
        variant = ''
        option = ''
        engine_file = self.__get_engine_file()
        if engine_file == None:
            return None

        dom = xml.dom.minidom.parse(engine_file)
        nodes = dom.getElementsByTagName('layout')[0].childNodes
        if len(nodes) > 0:
            layout = nodes[0].data
        if type(layout) == unicode:
            layout = str(layout)
        if layout != '':
            keymap = layout.strip()
        nodes = dom.getElementsByTagName('layout_variant')[0].childNodes
        if len(nodes) > 0:
            variant = nodes[0].data
        if type(variant) == unicode:
            variat = str(variant)
        if variant != '':
            keymap += '(' + varaint.strip() + ')'
        nodes = dom.getElementsByTagName('layout_option')[0].childNodes
        if len(nodes) > 0:
            option = nodes[0].data
        if type(option) == unicode:
            option = str(option)
        if option != '':
            keymap += '[' + option.strip() + ']'
        return keymap

    def __parse_keymap(self, keymap):
        layout = None
        variant = None
        option = None

        length = keymap.find('(')
        if length >= 0:
            if layout == None:
                layout = keymap[0:length]
            keymap = keymap[length + 1:]
            length = keymap.find(')')
            if length > 0:
                variant = keymap[0:length]
                keymap = keymap[length + 1:]
            else:
                print >> sys.stderr, 'Invalid keymap', keymap
                return ('', '', '')
        length = keymap.find('[')
        if length >= 0:
            if layout == None:
                layout = keymap[0:length]
            keymap = keymap[length + 1:]
            length = keymap.find(']')
            if length > 0:
                option = keymap[0:length]
                keymap = keymap[length + 1:]
            else:
                print >> sys.stderr, 'Invalid keymap', keymap
                return ('', '', '')

        if layout == None:
            layout = keymap
        if layout == None:
            layout = ''
        if variant == None:
            variant = ''
        if option == None:
            option = ''
        return (layout, variant, option)

    def __save_keymap(self):
        engine_file = self.__get_engine_file()
        if engine_file == None:
            return None

        (layout, variant, option) = self.__parse_keymap(self.__keymap)

        dom = xml.dom.minidom.parse(engine_file)
        nodes = dom.getElementsByTagName('layout')[0].childNodes
        if len(nodes) == 0:
            nodes.append(dom.createTextNode(layout))
        else:
            nodes[0].data = layout
        nodes = dom.getElementsByTagName('layout_variant')[0].childNodes
        if len(nodes) == 0:
            nodes.append(dom.createTextNode(variant))
        else:
            nodes[0].data = variant
        nodes = dom.getElementsByTagName('layout_option')[0].childNodes
        if len(nodes) == 0:
            nodes.append(dom.createTextNode(option))
        else:
            nodes[0].data = option
        nodes = dom.getElementsByTagName('symbol')[0].childNodes
        # unicode will causes UnicodeEncodeError in write stream.
        if len(nodes) > 0 and type(nodes[0].data) == unicode:
            nodes[0].data = nodes[0].data.encode('utf-8')

        user_config = path.join(self.__get_userhome(), '.config',
                                'ibus-anthy', 'engines.xml')
        dir = path.dirname(user_config)
        if not path.exists(dir):
            os.makedirs(dir, 0700)
        f = open(user_config, 'w')
        dom.writexml(f, '', '', '', 'utf-8')
        f.close()
        os.chmod(user_config, 0600)
        self.__keymap = None
        self.__run_message_dialog(_("Anthy keyboard layout is changed. "
                                    "Please restart ibus to reload the layout."))

    def __update_keymap_label(self):
        self.__resync_engine_file()
        prefs = self.__prefs
        keymap = self.__get_keymap()
        if keymap == None:
            return
        if keymap == '':
            keymap = 'default'
        keymap_list = prefs.get_value('common', 'keyboard-layouts')
        if keymap != None and not keymap in keymap_list:
            keymap_list.append(keymap)
        index = -1
        if keymap != None:
            index = keymap_list.index(keymap)
        model = Gtk.ListStore(str)
        for k in keymap_list:
            if k == 'default':
                k = _("Default")
            model.append([k])
        combobox = self.__builder.get_object('keymap:combobox_custom_table')
        combobox.set_model(model)
        combobox.set_active(0)
        if index >= 0:
            combobox.set_active(index)
        combobox.connect_after('changed',
                               self.on_cb_keymap_changed,
                               0)

    def __search_and_mark(self, buffer, text, start, end, onetime, forward):
        if forward:
            match = start.forward_search(text, 0, end)
        else:
            match = start.backward_search(text, 0, end)
        if match == None:
            return False
        match_start, match_end = match
        if onetime:
            buffer.place_cursor(match_start)
            buffer.select_range(match_start, match_end)
            return True
        buffer.apply_tag(buffer.tag_found, match_start, match_end)
        self.__search_and_mark(buffer, text, match_end, end, onetime, forward)
        return True

    def __filter_search(self, entry, onetime, forward):
        text = entry.get_text()
        self.__filter_timeout_id = 0

        text_view = entry.text_view
        buffer = text_view.get_buffer()
        start = buffer.get_start_iter()
        if onetime:
            bounds = buffer.get_selection_bounds()
            if len(bounds) != 0:
                start, end = bounds
                if forward:
                    start = end
        end = buffer.get_end_iter()
        if not forward:
            end = buffer.get_start_iter()
        if not onetime:
            buffer.remove_all_tags(start, end)
        if text == '':
            return
        found = self.__search_and_mark(buffer, text, start, end, onetime, forward)
        if not found and onetime and forward:
            end = start
            start = buffer.get_start_iter()
            self.__search_and_mark(buffer, text, start, end, onetime, forward)

    def __do_filter(self, entry):
        self.__filter_search(entry, False, True)
        return False

    def __filter_changed(self, entry):
        if self.__filter_timeout_id != 0:
            return
        self.__filter_timeout_id = GLib.timeout_add(150,
                                                    self.__do_filter,
                                                    entry)

    def __filter_key_release_event(self, entry, event):
        pressed, keyval = event.get_keyval()
        if keyval == IBus.KEY_Return:
            forward = True
            if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                forward = False
            self.__filter_search(entry, True, forward)
            text_view = entry.text_view
            buffer = text_view.get_buffer()
            text_view.scroll_to_mark(buffer.get_insert(),
                                     0.25, False, 0.0, 0.0)
        return False

    def on_selection_changed(self, widget, id):
        set_sensitive = lambda a, b: self.__builder.get_object(a).set_sensitive(b)
        flg = True if widget.get_selected()[1] else False
        for name in [['btn_default', 'btn_edit'], ['es:button_refresh', 'es:button_del']][id]:
            set_sensitive(name, flg)

    def on_selection_custom_key_table_changed(self, widget, id):
        l, i = widget.get_selected()
        # if 'combobox_custom_key_table' is changed,
        # 'treeview_custom_key_table' also receives this signal
        # but no selection.
        if i == None:
            return
        button = self.__builder.get_object('button_remove_custom_key')
        button.set_sensitive(True)

    def on_main_quit(self, widget, event):
        Gtk.main_quit()
        return True

    def on_btn_close_clicked(self, widget):
        Gtk.main_quit()

    def on_cb_keymap_changed(self, widget, id):
        it = widget.get_active()
        model = widget.get_model()
        keymap = model[it][0]
        if keymap == _("Default"):
            keymap = 'default'
        if self.__keymap == keymap:
            return
        self.__keymap = keymap
        self.__save_keymap()
        self.__keymap = None

    def on_cb_custom_key_table_changed(self, widget, user_data):
        prefs = self.__prefs
        tv = self.__builder.get_object('treeview_custom_key_table')
        mode = user_data
        id = widget.get_active()
        model = widget.get_model()
        method = model[id][1]
        if tv != None:
            for column in tv.get_columns():
                tv.remove_column(column)
            for child in tv.get_children():
                tv.remove(child)
        if mode == 'romaji':
            tv = self.__get_romaji_treeview_custom_key_table(method)
        elif mode == 'kana':
            prefs.set_value('kana-typing-rule', 'method', method)
            tv = self.__get_kana_treeview_custom_key_table(method)
        elif mode == 'thumb':
            # thumb uses all tables so do not save the method.
            tv = self.__get_thumb_treeview_custom_key_table(method)

    def on_btn_edit_clicked(self, widget):
        ls, it = self.__builder.get_object('shortcut').get_selection().get_selected()
        m = self.__builder.get_object('es:treeview').get_model()
        m.clear()
        for s in s_to_l(ls.get(it, 1)[0]):
            m.append([s])
        self.__builder.get_object('es:entry').set_text('')
        for w in ['es:checkbutton_ctrl', 'es:checkbutton_alt', 'es:checkbutton_shift']:
            self.__builder.get_object(w).set_active(False)
        dlg = self.__builder.get_object('edit_shortcut')
        dlg.set_transient_for(widget.get_toplevel())
        id = dlg.run()
        dlg.hide()
        if id == Gtk.ResponseType.OK:
            new = l_to_s([m[i][0] for i in range(len(m))])
            if new != ls.get(it, 1)[0]:
                group = self.__get_shortcut_group()
                self.__prefs.set_list_item('shortcut', group,
                                           ls.get(it, 0)[0], s_to_l(new))
                ls.set(it, 1, new)

    def on_btn_default_clicked(self, widget):
        ls, it = self.__builder.get_object('shortcut').get_selection().get_selected()
        group = self.__get_shortcut_group()
        shortcuts = self.__prefs.get_default_value('shortcut', group)
        new = l_to_s(shortcuts[ls.get(it, 0)[0]])
        if new != ls.get(it, 1)[0]:
            self.__prefs.set_list_item('shortcut', group,
                                       ls.get(it, 0)[0], s_to_l(new))
            ls.set(it, 1, new)

    def on_btn_romaji_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'romaji')

    def on_btn_kana_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'kana')

    def on_btn_thumb_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'thumb')

    def on_btn_add_custom_key(self, widget, user_data):
        prefs = self.__prefs
        input = self.__builder.get_object('entry_input_custom_key')
        output = self.__builder.get_object('entry_output_custom_key')
        left = self.__builder.get_object('entry_left_thumb_shift_custom_key')
        right = self.__builder.get_object('entry_right_thumb_shift_custom_key')
        model = self.__builder.get_object('treeview_custom_key_table').get_model()
        combobox = self.__builder.get_object('combobox_custom_key_table')
        id = combobox.get_active()
        model_combobox = combobox.get_model()
        method = model_combobox[id][1]
        type = user_data
        section = None
        key = input.get_text()
        value = output.get_text()
        left_text = left.get_text()
        right_text = right.get_text()

        if key == None:
            self.__run_message_dialog(_("Please specify Input Chars"))
            return
        elif value == None:
            self.__run_message_dialog(_("Please specify Output Chars"))
            return
        elif type == 'thumb' and left_text == None:
            self.__run_message_dialog(_("Please specify Left Thumb Shift Chars"))
            return
        elif type == 'thumb' and right_text == None:
            self.__run_message_dialog(_("Please specify Right Thumb Shift Chars"))
            return

        if type == 'romaji':
            section = 'romaji-typing-rule'
            model.append([type, key, value])
        elif type == 'kana':
            section = 'kana-typing-rule'
            model.append([type, key, value])
        elif type == 'thumb':
            section = 'thumb-typing-rule'
            model.append([type, key, value, left_text, right_text])
        if section == None:
            self.__run_message_dialog(_("Your custom key is not assigned in any sections. Maybe a bug."))
            return
        gkey = prefs.typing_to_config_key(key)
        if gkey == '':
            return
        key = gkey
        if type != 'thumb':
            prefs.set_list_item(section, 'list', (method, key), value)
        else:
            prefs.set_list_item(section, 'list',
                                (method, key), [value, right_text, left_text])
            left.set_text('')
            right.set_text('')
        input.set_text('')
        output.set_text('')

    def on_btn_remove_custom_key(self, widget, user_data):
        prefs = self.__prefs
        combobox = self.__builder.get_object('combobox_custom_key_table')
        id = combobox.get_active()
        model_combobox = combobox.get_model()
        method = model_combobox[id][1]
        tv = user_data
        l, i = tv.get_selection().get_selected()
        type = l[i][0]
        key = l[i][1]
        section = None
        if type == 'romaji':
            section = 'romaji-typing-rule'
        elif type == 'kana':
            section = 'kana-typing-rule'
        elif type == 'thumb':
            section = 'thumb-typing-rule'
        if section == None:
            self.__run_message_dialog(_("Your custom key is not assigned in any sections. Maybe a bug."))
            return
        gkey = prefs.typing_to_config_key(key)
        if gkey == '':
            return
        key = gkey
        prefs.delete_list_item(section, 'list', (method, key))
        l.remove(i)
        widget.set_sensitive(False)

    def on_btn_thumb_key_clicked(self, widget):
        if Gtk.Buildable.get_name(widget) == 'thumb:button_ls':
            entry = 'thumb:ls'
        elif Gtk.Buildable.get_name(widget) == 'thumb:button_rs':
            entry = 'thumb:rs'
        else:
            return
        text = self.__builder.get_object(entry).get_text()
        tv = self.__builder.get_object('es:treeview')
        m = tv.get_model()
        m.clear()
        if text != None:
            m.append([text])
            i = m.get_iter_first()
            tv.get_selection().select_iter(i)
        self.__builder.get_object('es:entry').set_text('')
        self.__builder.get_object('es:button_add').hide()
        self.__builder.get_object('es:button_refresh').show()
        self.__builder.get_object('es:button_del').hide()
        for w in ['es:checkbutton_ctrl', 'es:checkbutton_alt', 'es:checkbutton_shift']:
            self.__builder.get_object(w).set_active(False)
        dlg = self.__builder.get_object('edit_shortcut')
        dlg.set_transient_for(widget.get_toplevel())
        id = dlg.run()
        dlg.hide()
        self.__builder.get_object('es:button_add').show()
        self.__builder.get_object('es:button_refresh').hide()
        self.__builder.get_object('es:button_del').show()
        if id == Gtk.ResponseType.OK:
            l, i = tv.get_selection().get_selected()
            new = l[i][0]
            if new != text:
                section, key = self.__get_section_key(entry)
                self.__prefs.set_value(section, key, new)
                self.__builder.get_object(entry).set_text(new)

    def on_btn_dict_command_clicked(self, widget):
        if Gtk.Buildable.get_name(widget) == 'dict:btn_edit_dict_command':
            key = 'dict-admin-command'
        elif Gtk.Buildable.get_name(widget) == 'dict:btn_add_word_command':
            key = 'add-word-command'
        else:
            return
        command = self.__prefs.get_value('common', key)
        if not path.exists(command[0]):
            self.__run_message_dialog(_("Your file does not exist: ") + command[0],
                                      Gtk.MessageType.ERROR)
            return
        os.spawnl(os.P_NOWAIT, *command)

    def on_btn_dict_add_clicked(self, widget):
        file = None
        id = None
        dlg = None

        if Gtk.Buildable.get_name(widget) == 'dict:btn_add':
            dlg = Gtk.FileChooserDialog(title=_("Open Dictionary File"),
                                        transient_for=widget.get_toplevel(),
                                        action=Gtk.FileChooserAction.OPEN)
            buttons=(_("_Cancel"), Gtk.ResponseType.CANCEL,
                     _("_Open"), Gtk.ResponseType.OK)
            dlg.add_buttons(*buttons)
        if Gtk.Buildable.get_name(widget) == 'dict:btn_edit':
            dlg = Gtk.Dialog(title=_("Edit Dictionary File"),
                             transient_for=widget.get_toplevel())
            buttons=(_("_Cancel"), Gtk.ResponseType.CANCEL,
                     _("_OK"), Gtk.ResponseType.OK)
            dlg.add_buttons(*buttons)

        assert(dlg != None), 'Button name is undefined.'
        vbox = self.__builder.get_object('dict:add_extra_vbox')
        if Gtk.Buildable.get_name(widget) == 'dict:btn_add':
            # Need to init for the second time
            self.__init_dict_chooser_dialog()
            dlg.set_extra_widget(vbox)
        if Gtk.Buildable.get_name(widget) == 'dict:btn_edit':
            id = self.__set_selected_dict_to_dialog()
            if id == None:
                self.__run_message_dialog(_("Your choosed file is not correct."),
                                          Gtk.MessageType.ERROR)
                return
            parent_vbox = dlg.vbox
            parent_vbox.add(vbox)
        vbox.show_all()

        if dlg.run() == Gtk.ResponseType.OK:
            if Gtk.Buildable.get_name(widget) == 'dict:btn_add':
                file = dlg.get_filename()
                if file[0] != '/':
                    dir = dlg.get_current_folder()
                    file = dir + '/' + file
                self.__append_user_dict_from_dialog(file, None, True)
            elif Gtk.Buildable.get_name(widget) == 'dict:btn_edit':
                self.__append_user_dict_from_dialog(None, id, False)
        dlg.hide()
        vbox.unparent()

    def on_btn_dict_delete_clicked(self, widget):
        l, i = self.__builder.get_object('dict:view').get_selection().get_selected()

        if not i:
            return
        selected_id = l.get_value(i, 0)

        if selected_id == None:
            return
        dict_item = self.__prefs.get_value('dict', 'list')[selected_id]
        if dict_item.is_system:
            self.__run_message_dialog(_("You cannot delete the system dictionary."),
                                      Gtk.MessageType.ERROR)
            return

        file = self.__get_dict_file_from_id(selected_id)
        if file != None:
            order = self.__prefs.get_value('dict', 'order')
            order.remove(selected_id)
            order = self.__prefs.set_value('dict', 'order', order)
            self.__prefs.delete_list_item('dict', 'files', selected_id)
            self.__prefs.delete_list_item('dict', 'list', selected_id)
            l.remove(i)
            return

        l.remove(i)

    def on_btn_dict_view_clicked(self, widget):
        dict_file = None
        selected_id = self.__get_selected_dict_id()
        if selected_id == None:
            return

        dict_file = self.__get_dict_file_from_id(selected_id)
        if dict_file == None:
            self.__run_message_dialog(_("Your file is not good."),
                                      Gtk.MessageType.ERROR)
            return
        if not path.exists(dict_file[0]):
            self.__run_message_dialog(_("Your file does not exist: ") + dict_file[0],
                                      Gtk.MessageType.ERROR)
            return

        # The selected id is already quoted.
        dicts = self.__prefs.get_value('dict', 'list')
        dict_item = dicts[selected_id]
        nline = dict_item.preview_lines
        encoding = dict_item.encoding

        lines = '';
        for i, line in enumerate(file(dict_file[0])):
            if nline >= 0 and i >= nline:
                break;
            lines = lines + line
        if encoding != None and encoding != 'utf-8':
            lines = unicode(lines, encoding).encode('utf-8')

        dlg = Gtk.Dialog(title=_("View Dictionary File"),
                         transient_for=widget.get_toplevel())
        buttons=(_("_OK"), Gtk.ResponseType.OK)
        dlg.add_buttons(*buttons)
        buffer = Gtk.TextBuffer()
        buffer.set_text (lines)
        buffer.tag_found = buffer.create_tag('found', background = 'yellow')
        text_view = Gtk.TextView.new_with_buffer(buffer)
        text_view.set_editable(False)
        sw = Gtk.ScrolledWindow()
        sw.add(text_view)
        sw.set_min_content_height(400)
        parent_vbox = dlg.vbox
        parent_vbox.add(sw)
        sw.show_all()
        dlg.set_default_size(500, 500)
        self.__filter_timeout_id = 0

        if hasattr(Gtk, 'SearchEntry') and \
           hasattr(Gtk, 'SearchEntryClass') and \
           hasattr(Gtk.SearchEntryClass, 'search_changed'):
            filter_entry = Gtk.SearchEntry(hexpand = True,
                                           margin_left = 6,
                                           margin_right = 6,
                                           margin_top = 6,
                                           margin_bottom = 6)
            filter_entry.text_view = text_view
            filter_entry.connect('search-changed', self.__filter_changed)
            filter_entry.connect('key-release-event',
                                 self.__filter_key_release_event)
            parent_vbox.add(filter_entry)
            filter_entry.show_all()

        sw.show_all()
        dlg.run()
        dlg.destroy()

    def on_btn_dict_order_clicked(self, widget):
        l, it = self.__builder.get_object('dict:view').get_selection().get_selected()

        if not it:
            return
        selected_path = l.get_path(it)
        selected_id = l.get_value(it, 0)
        index = selected_path.get_indices()[0]

        if Gtk.Buildable.get_name(widget) == 'dict:btn_up':
            if index <= 0:
                return
            next_path = (index - 1, )
        elif Gtk.Buildable.get_name(widget) == 'dict:btn_down':
            if index + 1 >= len(l):
                return
            next_path = (index + 1, )
        next_it = l.get_iter(next_path)
        if next_it:
            l.swap(it, next_it)

        order = self.__prefs.get_value('dict', 'order')
        if len(order) == 0:
            order = list(self.__prefs.get_value('dict', 'files').keys())
        i = order.index(selected_id)

        if Gtk.Buildable.get_name(widget) == 'dict:btn_up':
            if i <= 0:
                return
            next_i = i - 1
        elif Gtk.Buildable.get_name(widget) == 'dict:btn_down':
            if i + 1 >= len(order):
                return
            next_i = i + 1
        f = order[i]
        order[i] = order[next_i]
        order[next_i] = f
        self.__prefs.set_value('dict', 'order', order)

    def on_shortcut_type_changed(self, widget):
        ls = self.__builder.get_object('shortcut').get_model()
        ls.clear()

        group = self.__get_shortcut_group()
        shortcuts = self.__prefs.get_value('shortcut', group)
        for k in shortcuts.keys():
            ls.append([k, l_to_s(shortcuts[k])])

        section, key = self.__get_section_key(Gtk.Buildable.get_name(widget))
        self.__prefs.set_value(section, key, group)

    def on_shortcut_key_release_event(self, widget, event):
        if event.hardware_keycode in [36, 65]:
            self.on_btn_edit_clicked(widget)

    def on_shortcut_click_event(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            widget.dc = True
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            if hasattr(widget, 'dc') and widget.dc:
                self.on_btn_edit_clicked(widget)
                widget.dc = False

    def on_key_input_dialog_key_press_event(self, widget, event):
        widget.e = (event.keyval, event.get_state())
        return True

    def on_key_input_dialog_key_release_event(self, widget, event):
        widget.response(Gtk.ResponseType.OK)
        return True

    def on_entry_custom_key_changed(self, widget, user_data):
        mode = user_data
        input = self.__builder.get_object('entry_input_custom_key')
        output = self.__builder.get_object('entry_output_custom_key')
        left = self.__builder.get_object('entry_left_thumb_shift_custom_key')
        right = self.__builder.get_object('entry_right_thumb_shift_custom_key')
        button = self.__builder.get_object('button_add_custom_key')
        if mode != 'thumb':
            if input.get_text() != '' and output.get_text() != '':
                button.set_sensitive(True)
            else:
                button.set_sensitive(False)
        else:
            if input.get_text() != '' and output.get_text() != '' and \
                left.get_text() != '' and right.get_text() != '':
                button.set_sensitive(True)
            else:
                button.set_sensitive(False)

    def on_entry_dict_command_changed(self, widget):
        if not widget.get_text():
            return
        list = widget.get_text().split()
        if len(list) == 0:
            return
        elif list[0][0] == '/':
            if len(list) == 1:
                list.append(list[0][list[0].rfind('/') + 1:])
            else:
                list.insert(1, list[0][list[0].rfind('/') + 1:])
        else:
            if len(list) == 1:
                list[0] = '/usr/bin/' + list[0]
            else:
                list.insert(0, '/usr/bin/' + list[0])
                list[1] = list[1][list[1].rfind('/') + 1:]
        if Gtk.Buildable.get_name(widget) == 'dict:entry-edit-dict-command':
            key = 'dict-admin-command'
        elif Gtk.Buildable.get_name(widget) == 'dict:entry-add-word-command':
            key = 'add-word-command'
        else:
            return
        self.__prefs.set_value('common', key, list)

    def on_es_entry_changed(self, widget):
        if not widget.get_text():
            self.__builder.get_object('es:button_add').set_sensitive(False)
        else:
            self.__builder.get_object('es:button_add').set_sensitive(True)

    def on_es_button_run_input_clicked(self, widget):
        dlg = self.__builder.get_object('key_input_dialog')
        dlg.set_transient_for(widget.get_toplevel())
        dlg.set_markup('<big><b>%s</b></big>' % _("Please press a key (or a key combination)"))
        dlg.format_secondary_text(_("The dialog will be closed when the key is released"))
        id = dlg.run()
        dlg.hide()
        if id == Gtk.ResponseType.OK:
            key, state = dlg.e
            if (state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) and
                    ord('a') <= key <= ord('z')):
                key = ord(chr(key).upper())
            self.__builder.get_object('es:entry').set_text(IBus.keyval_name(key))

            for w, i in [('es:checkbutton_ctrl', IBus.ModifierType.CONTROL_MASK),
                         ('es:checkbutton_alt', IBus.ModifierType.MOD1_MASK),
                         ('es:checkbutton_shift', IBus.ModifierType.SHIFT_MASK)]:
                self.__builder.get_object(w).set_active(True if state & i else False)

    def on_es_button_add_clicked(self, widget):
        s = self.__builder.get_object('es:entry').get_text()
        if not s or not IBus.keyval_from_name(s):
            dlg = self.__builder.get_object('invalid_keysym')
            dlg.set_transient_for(widget.get_toplevel())
            dlg.set_markup('<big><b>%s</b></big>' % _("Invalid keysym"))
            dlg.format_secondary_text(_("This keysym is not valid"))
            dlg.run()
            dlg.hide()
            return True
        for w, m in [('es:checkbutton_ctrl', 'Ctrl+'),
                     ('es:checkbutton_alt', 'Alt+'),
                     ('es:checkbutton_shift', 'Shift+')]:
            if self.__builder.get_object(w).get_active():
                s = m + s
        l = self.__builder.get_object('es:treeview').get_model()
        for i in range(len(l)):
            if l[i][0] == s:
                return True
        l.append([s])

    def on_es_button_refresh_clicked(self, widget):
        s = self.__builder.get_object('es:entry').get_text()
        if not s or not IBus.keyval_from_name(s):
            dlg = self.__builder.get_object('invalid_keysym')
            dlg.set_transient_for(widget.get_toplevel())
            dlg.set_markup('<big><b>%s</b></big>' % _("Invalid keysym"))
            dlg.format_secondary_text(_("This keysym is not valid"))
            dlg.run()
            dlg.hide()
            return True
        for w, m in [('es:checkbutton_ctrl', 'Ctrl+'),
                     ('es:checkbutton_alt', 'Alt+'),
                     ('es:checkbutton_shift', 'Shift+')]:
            if self.__builder.get_object(w).get_active():
                s = m + s
        tv = self.__builder.get_object('es:treeview')
        l, i = tv.get_selection().get_selected()
        l[i][0] = s
        return True

    def on_es_button_del_clicked(self, widget):
        tv = self.__builder.get_object('es:treeview')
        l, i = tv.get_selection().get_selected()
        if i:
            l.remove(i)

    def run(self):
        Gtk.main()

if __name__ == '__main__':
    AnthySetup().run()

