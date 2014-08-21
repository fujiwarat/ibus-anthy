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

from os import environ, getuid, path
import os, sys
import locale
import xml.dom.minidom
import gettext
from gettext import dgettext

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

        # IBus.Bus() calls ibus_bus_new().
        # Gtk.Builder().add_from_file() also calls ibus_bus_new_async()
        # via ibus_im_context_new().
        # Then if IBus.Bus() is called after Gtk.Builder().add_from_file(),
        # the connection delay would be happened without an async
        # finish function.
        ibus_address = IBus.get_address()
        bus = None
        if ibus_address != None:
            bus = IBus.Bus(connect_async='True')

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

        if ibus_address == None:
            builder.connect_signals(self)
            # self.__run_message_dialog needs self.__builder.
            self.__run_message_dialog(_("ibus is not running."),
                                      Gtk.MessageType.ERROR)
            return

        if bus.is_connected():
            self.__init_bus_connected(bus)
        else:
            bus.connect('connected', self.__init_bus_connected)

    def __init_bus_connected(self, bus):
        self.__config = bus.get_config()
        builder = self.__builder

        self.__thumb_kb_layout_mode = None
        self.__thumb_kb_layout = None
        self.__japanese_ordered_dict = {}
        self.prefs = prefs = AnthyPrefs(None, self.__config)

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

        for name in ['input_mode', 'typing_method', 'conversion_segment_mode',
                     'period_style', 'symbol_style', 'ten_key_mode',
                     'behavior_on_focus_out', 'behavior_on_period',
                     'half_width_symbol', 'half_width_number', 'half_width_space',
                     'latin_with_shift',
                     'thumb:keyboard_layout_mode', 'thumb:keyboard_layout',
                     'thumb:fmv_extension', 'thumb:handakuten',
                     'show_input_mode_icon']:
            section, key = self.__get_section_key(name)
            builder.get_object(name).set_active(prefs.get_value(section, key))

        tv = builder.get_object('menu_visible:treeview')
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
        s_type = prefs.get_value('common', 'shortcut_type')
        s_type = s_type if s_type in l else 'default'
        builder.get_object('shortcut_type').set_active(l.index(s_type))

        builder.get_object('page_size').set_value(prefs.get_value('common',
                                                                  'page_size'))

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
        sec = 'shortcut/' + s_type
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])
        tv.set_model(ls)

        self.__keymap = None
        GLib.idle_add(self.__update_keymap_label,
                      priority = GLib.PRIORITY_LOW)

        self.__thumb_kb_layout_mode = builder.get_object('thumb:keyboard_layout_mode')
        self.__thumb_kb_layout = builder.get_object('thumb:keyboard_layout')
        self.__set_thumb_kb_label()

        for name in ['thumb:ls', 'thumb:rs']:
            section, key = self.__get_section_key(name)
            builder.get_object(name).set_text(prefs.get_value(section, key))

        tv = builder.get_object('es:treeview')
        tv.append_column(Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=0))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 1)
        tv.set_model(Gtk.ListStore(str))

        key = 'dict_admin_command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry_edit_dict_command'
        builder.get_object(name).set_text(cli)
        key = 'add_word_command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry_add_word_command'
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
        japanese_ordered_list = self.prefs.get_japanese_ordered_list()
        for index, c in enumerate(japanese_ordered_list):
            japanese_ordered_dict[c] = index
        self.__japanese_ordered_dict = japanese_ordered_dict;

    def __init_about_vbox(self, icon_path):
        about_dialog = self.__builder.get_object('about_dialog')
        about_vbox = self.__builder.get_object('about_vbox')
        about_dialog.set_version(self.prefs.get_version())
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
        if section == 'common':
            if name == 'show_input_mode_icon':
                key = 'show-input-mode-icon'
        return (section, key)

    def __run_message_dialog(self, message, type=Gtk.MessageType.INFO):
        dlg = Gtk.MessageDialog(
                transient_for=self.__builder.get_object('main'),
                message_type=type,
                buttons=Gtk.ButtonsType.OK,
                text=message)
        dlg.run()
        dlg.destroy()

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
        prefs = self.prefs
        enabled = not model[path][1]
        model[path][1] = enabled
        key = model[path][0]
        prefs.set_value('common', key, enabled)
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def __toggle_menu_visible_cell_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('menu_visible:treeview').get_model()
        active = l.get_value(iter, id)
        renderer.set_property('active', active)

    def __text_menu_visible_cell_cb(self, column, renderer, model, iter, id):
        l = self.__builder.get_object('menu_visible:treeview').get_model()
        text = l.get_value(iter, id)
        renderer.set_property('text', text)

    def __append_menus_in_model(self):
        prefs = self.prefs
        l = self.__builder.get_object('menu_visible:treeview').get_model()
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
        prefs = self.prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section_base = 'romaji_typing_rule'
        section = section_base + '/' + prefs.str(method)
        for key in prefs.keys(section):
            key = prefs.str(key)
            value = prefs.get_value(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = prefs.str(value)
        for key in prefs.get_value(section_base, 'newkeys'):
            key = prefs.str(key)
            value = self.prefs.get_value_direct(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = prefs.str(value)
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
        prefs = self.prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section_base = 'kana_typing_rule'
        section = section_base + '/' + prefs.str(method)
        for key in prefs.keys(section):
            key = prefs.str(key)
            value = prefs.get_value(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = prefs.str(value)
        for key in prefs.get_value(section_base, 'newkeys'):
            key = prefs.str(key)
            value = self.prefs.get_value_direct(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and value != '':
                rule[ch] = prefs.str(value)
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
        prefs = self.prefs
        rule = {}
        ls = Gtk.ListStore(str, str, str, str, str)
        tv = self.__builder.get_object('treeview_custom_key_table')
        section_base = 'thumb_typing_rule'
        section = section_base + '/' + prefs.str(method)
        for key in prefs.keys(section):
            key = prefs.str(key)
            value = prefs.get_value(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and len(value) == 3 and \
                ((value[0] != None and value[0] != '') or \
                 (value[1] != None and value[1] != '') or \
                 (value[2] != None and value[2] != '')):
                rule[ch] = {}
                rule[ch][0] = prefs.str(value[0])
                rule[ch][1] = prefs.str(value[1])
                rule[ch][2] = prefs.str(value[2])
        for key in prefs.get_value(section_base, 'newkeys'):
            key = prefs.str(key)
            value = self.prefs.get_value_direct(section, key)
            ch = prefs.typing_from_config_key(key)
            if ch == '':
                continue
            # config.set_value(key, None) is not supported.
            if value != None and len(value) == 3 and \
                ((value[0] != None and value[0] != '') or \
                 (value[1] != None and value[1] != '') or \
                 (value[2] != None and value[2] != '')):
                rule[ch] = {}
                rule[ch][0] = prefs.str(value[0])
                rule[ch][1] = prefs.str(value[1])
                rule[ch][2] = prefs.str(value[2])
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
        prefs = self.prefs
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
                           ['nicola_j_table', _("NICOLA-J key extension")],
                           ['nicola_a_table', _("NICOLA-A key extension")],
                           ['nicola_f_table', _("NICOLA-F key extension")],
                           ['kb231_j_fmv_table', _("FMV KB231-J key extension")],
                           ['kb231_a_fmv_table', _("FMV KB231-A key extension")],
                           ['kb231_f_fmv_table', _("FMV KB231-F key extension")],
                           ['kb611_j_fmv_table', _("FMV KB611-J key extension")],
                           ['kb611_a_fmv_table', _("FMV KB611-A key extension")],
                           ['kb611_f_fmv_table', _("FMV KB611-F key extension")],
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
            method = prefs.get_value('romaji_typing_rule', 'method')
            if method == None:
                method = 'default'
            tv = self.__get_romaji_treeview_custom_key_table(method)
        if mode == 'kana':
            method = prefs.get_value('kana_typing_rule', 'method')
            if method == None:
                method = 'jp'
            tv = self.__get_kana_treeview_custom_key_table(method)
        if mode == 'thumb':
            method = prefs.get_value('thumb_typing_rule', 'method')
            if method == None:
                method = 'base'
            tv = self.__get_thumb_treeview_custom_key_table(method)

        self.__connect_dialog_custom_key_table_buttons(mode)

        id = 0
        # thumb uses all tables so the default is always 0.
        if mode != 'thumb':
            for index, labels in enumerate(list_labels):
                if labels[0] == method:
                    id = index
                    break
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
        layout_mode = self.prefs.get_value(section, key)
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
        files = self.prefs.get_value('dict', 'files')
        retval = None

        for file in files:
            id = self.__get_quoted_id(file)
            # The selected_id is already quoted.
            if selected_id == id:
                retval = file
                break
        return retval

    def __is_system_dict_file_from_id(self, selected_id):
        prefs = self.prefs
        section = 'dict/file/' + selected_id
        key = 'is_system'

        if key not in prefs.keys(section):
            return False
        return prefs.get_value(section, key)

    def __append_dict_id_in_model(self, id, is_gettext):
        prefs = self.prefs
        section = 'dict/file/' + id
        # user value is dbus.String
        prefs.set_value(section, 'short_label',
                        prefs.str(prefs.get_value(section, 'short_label')))
        prefs.set_value(section, 'long_label',
                        prefs.str(prefs.get_value(section, 'long_label')))
        short_label = prefs.get_value(section, 'short_label')
        long_label = prefs.get_value(section, 'long_label')
        embed = prefs.get_value(section, 'embed')
        single = prefs.get_value(section, 'single')
        reverse = prefs.get_value(section, 'reverse')
        if is_gettext:
            long_label = _(long_label)
        l = self.__builder.get_object('dict:view').get_model()
        l.append([id, short_label, long_label, embed, single, reverse])

    def __append_dicts_in_model(self):
        prefs = self.prefs
        for file in prefs.get_value('dict', 'files'):
            if not path.exists(file):
                continue
            id = self.__get_quoted_id(file)
            section = 'dict/file/' + id
            if section not in prefs.sections():
                self.__fetch_dict_values(section)
            is_system_dict = self.__is_system_dict_file_from_id(id)
            self.__append_dict_id_in_model(id, is_system_dict)

    def __append_user_dict_from_dialog(self, file, id, new):
        files = self.prefs.get_value('dict', 'files')

        if new:
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
            files.append(file)
            self.prefs.set_value('dict', 'files', files)

        if short_label == None or short_label == '':
                short_label = id[0]
        if long_label == None or long_label == '':
                long_label = id
        self.__update_dict_values(new, id, short_label, long_label, embed, single, reverse)
        self.__builder.get_object('btn_apply').set_sensitive(True)
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

        is_system_dict = self.__is_system_dict_file_from_id(selected_id)

        prefs = self.prefs
        section = 'dict/file/' + selected_id
        short_label = prefs.get_value(section, 'short_label')
        long_label = prefs.get_value(section, 'long_label')
        embed = prefs.get_value(section, 'embed')
        single = prefs.get_value(section, 'single')
        reverse = prefs.get_value(section, 'reverse')

        if len(prefs.unicode(short_label)) > 1:
            short_label = prefs.unicode(short_label)[0].encode('utf-8')
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

    def __fetch_dict_values(self, section):
        prefs = self.prefs
        prefs.set_new_section(section)
        prefs.set_new_key(section, 'short_label')
        prefs.fetch_item(section, 'short_label')
        # user value is dbus.String
        prefs.set_value(section, 'short_label',
                        prefs.str(prefs.get_value(section, 'short_label')))
        prefs.set_new_key(section, 'long_label')
        prefs.fetch_item(section, 'long_label')
        prefs.set_value(section, 'long_label',
                        prefs.str(prefs.get_value(section, 'long_label')))
        prefs.set_new_key(section, 'embed')
        prefs.fetch_item(section, 'embed')
        prefs.set_new_key(section, 'single')
        prefs.fetch_item(section, 'single')
        prefs.set_new_key(section, 'reverse')
        prefs.fetch_item(section, 'reverse')

    def __update_dict_values(self, new, id, short_label, long_label, embed, single, reverse):
        prefs = self.prefs
        section = 'dict/file/' + id
        if section not in prefs.sections():
            prefs.set_new_section(section)

        is_system_dict = self.__is_system_dict_file_from_id(id)
        if is_system_dict:
            if 'short_label' in prefs.keys(section):
                short_label = prefs.get_value(section, 'short_label')
            if 'long_label' in prefs.keys(section):
                long_label = prefs.get_value(section, 'long_label')

        if new:
            l = self.__builder.get_object('dict:view').get_model()
            l.append([id, short_label, long_label, embed, single, reverse])
        else:
            l, i = self.__builder.get_object('dict:view').get_selection().get_selected()
            if i :
                l[i] = [id, short_label, long_label, embed, single, reverse]

        key = 'short_label'
        prefs.set_value(section, key, short_label)
        key = 'long_label'
        prefs.set_value(section, key, long_label)
        key = 'embed'
        prefs.set_value(section, key, embed)
        key = 'single'
        prefs.set_value(section, key, single)
        key = 'reverse'
        prefs.set_value(section, key, reverse)

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
        prefs = self.prefs
        keymap = self.__get_keymap()
        if keymap == None:
            return
        if keymap == '':
            keymap = 'default'
        keymap_list = prefs.get_value('common', 'keyboard_layouts')
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

    def __save_preferences(self):
        self.prefs.commit_all()
        if self.__keymap != None:
            self.__save_keymap()

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

    def on_main_delete(self, widget, event):
        self.on_btn_cancel_clicked(widget)
        return True

    def on_btn_ok_clicked(self, widget):
        if self.__builder.get_object('btn_apply').get_state() == \
                Gtk.StateType.INSENSITIVE:
            Gtk.main_quit()
            return True
        dlg = self.__builder.get_object('quit_check')
        dlg.set_transient_for(widget.get_toplevel())
        dlg.set_markup('<big><b>%s</b></big>' % _("Confirmation"))
        dlg.format_secondary_text(
                _("You are about to close the setup dialog, is that OK?"))
        id = dlg.run()
        dlg.hide()
        if id == Gtk.ResponseType.YES:
            self.__save_preferences()
            Gtk.main_quit()
            return True

    def on_btn_cancel_clicked(self, widget):
        if self.__builder.get_object('btn_apply').get_state() == \
                Gtk.StateType.INSENSITIVE:
            Gtk.main_quit()
            return True
        dlg = self.__builder.get_object('quit_check_without_save')
        dlg.set_transient_for(widget.get_toplevel())
        dlg.set_markup('<big><b>%s</b></big>' % _("Notice!"))
        dlg.format_secondary_text(
                _("You are about to close the setup dialog without saving your changes, is that OK?"))
        id = dlg.run()
        dlg.hide()
        if id == Gtk.ResponseType.YES:
            Gtk.main_quit()
            return True

    def on_btn_apply_clicked(self, widget):
        self.__save_preferences()
        widget.set_sensitive(False)

    def on_cb_changed(self, widget):
        section, key = self.__get_section_key(Gtk.Buildable.get_name(widget))
        self.prefs.set_value(section, key, widget.get_active())
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_cb_keymap_changed(self, widget, id):
        it = widget.get_active()
        model = widget.get_model()
        keymap = model[it][0]
        if keymap == _("Default"):
            keymap = 'default'
        if self.__keymap == keymap:
            return
        self.__keymap = keymap
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_cb_custom_key_table_changed(self, widget, user_data):
        prefs = self.prefs
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
            prefs.set_value('kana_typing_rule', 'method', method)
            self.__builder.get_object('btn_apply').set_sensitive(True)
            tv = self.__get_kana_treeview_custom_key_table(method)
        elif mode == 'thumb':
            # thumb uses all tables so do not save the method.
            tv = self.__get_thumb_treeview_custom_key_table(method)

    def on_sb_changed(self, widget):
        section, key = self.__get_section_key(Gtk.Buildable.get_name(widget))
        self.prefs.set_value(section, key, widget.get_value_as_int())
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_ck_toggled(self, widget):
        section, key = self.__get_section_key(Gtk.Buildable.get_name(widget))
        self.prefs.set_value(section, key, widget.get_active())
        self.__builder.get_object('btn_apply').set_sensitive(True)
        if self.__thumb_kb_layout_mode and \
           Gtk.Buildable.get_name(widget) == \
               Gtk.Buildable.get_name(self.__thumb_kb_layout_mode):
            self.__set_thumb_kb_label()

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
                sec = self._get_shortcut_sec()
                self.prefs.set_value(sec, ls.get(it, 0)[0], s_to_l(new))
                ls.set(it, 1, new)
                self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_btn_default_clicked(self, widget):
        ls, it = self.__builder.get_object('shortcut').get_selection().get_selected()
        sec = self._get_shortcut_sec()
        new = l_to_s(self.prefs.default[sec][ls.get(it, 0)[0]])
        if new != ls.get(it, 1)[0]:
            self.prefs.set_value(sec, ls.get(it, 0)[0], s_to_l(new))
            ls.set(it, 1, new)
            self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_btn_romaji_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'romaji')

    def on_btn_kana_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'kana')

    def on_btn_thumb_custom_table_clicked(self, widget):
        self.__run_dialog_custom_key_table(widget, 'thumb')

    def on_btn_add_custom_key(self, widget, user_data):
        prefs = self.prefs
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
        section_base = None
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
            section_base = 'romaji_typing_rule'
            model.append([type, key, value])
        elif type == 'kana':
            section_base = 'kana_typing_rule'
            model.append([type, key, value])
        elif type == 'thumb':
            section_base = 'thumb_typing_rule'
            model.append([type, key, value, left_text, right_text])
        if section_base == None:
            self.__run_message_dialog(_("Your custom key is not assigned in any sections. Maybe a bug."))
            return
        gkey = prefs.typing_to_config_key(key)
        if gkey == '':
            return
        key = gkey
        section = section_base + '/' + method
        if key not in prefs.keys(section):
            # ibus does not support gconf_client_all_entries().
            # prefs.fetch_section() doesn't get the keys if they exist
            # in gconf only.
            # Use newkeys for that way.
            newkeys = prefs.get_value(section_base, 'newkeys')
            if key not in newkeys:
                newkeys.append(key)
                prefs.set_value(section_base, 'newkeys', newkeys)
        if type != 'thumb':
            prefs.set_value(section, key, value)
        else:
            prefs.set_value(section, key, [value, right_text, left_text])
            left.set_text('')
            right.set_text('')
        input.set_text('')
        output.set_text('')
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_btn_remove_custom_key(self, widget, user_data):
        prefs = self.prefs
        combobox = self.__builder.get_object('combobox_custom_key_table')
        id = combobox.get_active()
        model_combobox = combobox.get_model()
        method = model_combobox[id][1]
        tv = user_data
        l, i = tv.get_selection().get_selected()
        type = l[i][0]
        key = l[i][1]
        section_base = None
        if type == 'romaji':
            section_base = 'romaji_typing_rule'
        elif type == 'kana':
            section_base = 'kana_typing_rule'
        elif type == 'thumb':
            section_base = 'thumb_typing_rule'
        if section_base == None:
            self.__run_message_dialog(_("Your custom key is not assigned in any sections. Maybe a bug."))
            return
        section = section_base + '/' + method
        newkeys = prefs.get_value(section_base, 'newkeys')
        gkey = prefs.typing_to_config_key(key)
        if gkey == '':
            return
        key = gkey
        if key in newkeys:
            newkeys.remove(key)
            prefs.set_value(section_base, 'newkeys', newkeys)
        # config.set_value(key, None) is not supported.
        if type != 'thumb':
            prefs.set_value(section, key, '')
        else:
            prefs.set_value(section, key, ['', '', ''])
        l.remove(i)
        widget.set_sensitive(False)
        self.__builder.get_object('btn_apply').set_sensitive(True)

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
                self.prefs.set_value(section, key, new)
                self.__builder.get_object(entry).set_text(new)
                self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_btn_dict_command_clicked(self, widget):
        if Gtk.Buildable.get_name(widget) == 'dict:btn_edit_dict_command':
            key = 'dict_admin_command'
        elif Gtk.Buildable.get_name(widget) == 'dict:btn_add_word_command':
            key = 'add_word_command'
        else:
            return
        command = self.prefs.get_value('common', key)
        if not path.exists(command[0]):
            self.__run_message_dialog(_("Your file does not exist: ") + command[0],
                                      Gtk.MessageType.ERROR)
            return
        os.spawnl(os.P_NOWAIT, *command)

    def on_btn_dict_add_clicked(self, widget):
        file = None
        id = None

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
        if self.__is_system_dict_file_from_id(selected_id):
            self.__run_message_dialog(_("You cannot delete the system dictionary."),
                                      Gtk.MessageType.ERROR)
            return

        file = self.__get_dict_file_from_id(selected_id)
        if file != None:
            files = self.prefs.get_value('dict', 'files')
            files.remove(file)
            self.prefs.set_value('dict', 'files', files)
            self.__builder.get_object('btn_apply').set_sensitive(True)
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
        if not path.exists(dict_file):
            self.__run_message_dialog(_("Your file does not exist: ") + dict_file,
                                      Gtk.MessageType.ERROR)
            return

        if dict_file == None:
            return

        # The selected id is already quoted.
        section = 'dict/file/' + selected_id
        if 'preview_lines' not in self.prefs.keys(section):
            section = 'dict/file/default'
        nline = self.prefs.get_value(section, 'preview_lines')

        section = 'dict/file/' + selected_id
        if 'encoding' not in self.prefs.keys(section):
            section = 'dict/file/default'
        encoding = self.prefs.get_value(section, 'encoding')

        lines = '';
        for i, line in enumerate(file(dict_file)):
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
        dict_file = None
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

        dict_file = self.__get_dict_file_from_id(selected_id)
        files = self.prefs.get_value('dict', 'files')

        if dict_file == None:
            return

        i = files.index(dict_file)
        if Gtk.Buildable.get_name(widget) == 'dict:btn_up':
            if i <= 0:
                return
            next_i = i - 1
        elif Gtk.Buildable.get_name(widget) == 'dict:btn_down':
            if i + 1 >= len(dict_file):
                return
            next_i = i + 1
        f = files[i]
        files[i] = files[next_i]
        files[next_i] = f
        self.prefs.set_value('dict', 'files', files)
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def _get_shortcut_sec(self):
        l = ['default', 'atok', 'wnn']
        iter = self.__builder.get_object('shortcut_type').get_active_iter()
        model = self.__builder.get_object('shortcut_type').get_model()
        s_type = model[iter][0].lower()
        return 'shortcut/' + (s_type if s_type in l else 'default')

    def on_shortcut_type_changed(self, widget):
        ls = self.__builder.get_object('shortcut').get_model()
        ls.clear()

        sec = self._get_shortcut_sec()
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])

        section, key = self.__get_section_key(Gtk.Buildable.get_name(widget))
        self.prefs.set_value(section, key, sec[len('shortcut/'):])
        self.__builder.get_object('btn_apply').set_sensitive(True)

    def on_shortcut_key_release_event(self, widget, event):
        if event.hardware_keycode in [36, 65]:
            self.on_btn_edit_clicked(None)

    def on_shortcut_click_event(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            widget.dc = True
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            if hasattr(widget, 'dc') and widget.dc:
                self.on_btn_edit_clicked(None)
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
        if list[0][0] == '/':
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
        if Gtk.Buildable.get_name(widget) == 'dict:entry_edit_dict_command':
            key = 'dict_admin_command'
        elif Gtk.Buildable.get_name(widget) == 'dict:entry_add_word_command':
            key = 'add_word_command'
        else:
            return
        self.prefs.set_value('common', key, list)
        self.__builder.get_object('btn_apply').set_sensitive(True)

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

