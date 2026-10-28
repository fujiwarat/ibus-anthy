#!/usr/bin/python3
# -*- coding: utf-8 -*-

from __future__ import print_function

from gi import require_versions as gi_require_versions
gi_require_versions({'GLib': '2.0', 'Gio': '2.0', 'GObject': '2.0',
                     'IBus': '1.0'})
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import IBus

try:
    gi_require_versions({'Gdk': '4.0', 'Gtk': '4.0'})
except ValueError:
    gi_require_versions({'Gdk': '3.0', 'Gtk': '3.0'})

from gi.repository import Gdk
from gi.repository import Gtk

import argparse
import getopt
import os
import sys
import subprocess
import unittest

TAP_MODULE_NONE, \
TAP_MODULE_TAPPY, \
TAP_MODULE_PYCOTAP = list(range(3))

tap_module = TAP_MODULE_NONE

# Need to flush the output against Gtk.main()
def printflush(sentence):
    try:
        print(sentence, flush=True)
    except IOError:
        pass

def printerr(sentence):
    try:
        print(sentence, flush=True, file=sys.stderr)
    except IOError:
        pass

try:
    from tap import TAPTestRunner
    tap_module = TAP_MODULE_TAPPY
    printflush('## Load tappy')
except ModuleNotFoundError:
    try:
        from pycotap import TAPTestRunner
        from pycotap import LogMode
        tap_module = TAP_MODULE_PYCOTAP
        printflush('## Load pycotap')
    except ModuleNotFoundError as err:
        printflush('## Ignore tap module: %s' % str(err))

PY3K = sys.version_info >= (3, 0)
DONE_EXIT = True

if 'IBUS_ANTHY_ENGINE_PATH' in os.environ:
    engine_paths = os.environ['IBUS_ANTHY_ENGINE_PATH']
    if engine_paths != None and engine_paths != '':
        for engine_path in engine_paths.split(':'):
            sys.path.append(engine_path)
if 'IBUS_ANTHY_SETUP_PATH' in os.environ:
    setup_paths = os.environ['IBUS_ANTHY_SETUP_PATH']
    if setup_paths != None and setup_paths != '':
        for setup_path in setup_paths.split(':'):
            sys.path.append(setup_path)
sys.path.append('/usr/share/ibus-anthy/engine')

from anthycases import TestCases


@unittest.skipIf(Gdk.Display.get_default() == None, 'Display cannot be open.')
class AnthyTest(unittest.TestCase):
    global DONE_EXIT
    ENGINE_PATH = '/com/redhat/IBus/engines/Anthy/Test/Engine'

    @classmethod
    def setUpClass(cls):
        IBus.init()

    def setUp(self):
        self.__id = 0
        self.__engine_is_focused = False
        self.__idle_count = 0
        self.__idle_loop = None
        self.__test_index = 0
        self.__preedit_changes = 0
        self.__preedit_prev = None
        self.__conversion_index = 0
        self.__conversion_spaces = 0
        self.__commit_done = False
        self.__engine = None
        self.__list_toplevel = False
        self.__is_wayland = False
        display = Gdk.Display.get_default()
        if GObject.type_name(display.__gtype__) == 'GdkWaylandDisplay':
            self.__is_wayland = True

    def register_ibus_engine(self):
        printflush('## Registering engine')
        self.__bus = IBus.Bus()
        if not self.__bus.is_connected():
            self.fail('ibus-daemon is not running')
            return False;
        self.__bus.get_connection().signal_subscribe('org.freedesktop.DBus',
                                              'org.freedesktop.DBus',
                                              'NameOwnerChanged',
                                              '/org/freedesktop/DBus',
                                              None,
                                              0,
                                              self.__name_owner_changed_cb,
                                              self.__bus)
        #self.__factory = factory.EngineFactory(self.__bus)
        self.__factory = IBus.Factory(
                object_path=IBus.PATH_FACTORY,
                connection=self.__bus.get_connection())
        self.__factory.connect('create-engine', self.__create_engine_cb)
        #command_line = '/usr/libexec/ibus-engine-anthy'
        self.__component = IBus.Component(name='org.freedesktop.IBus.Anthy.Test',
                                          description='Test Anthy Component',
                                          version='0.0.1',
                                          license='GPL',
                                          author='Takao Fujiwara <takao.fujiwara1@gmail.com>',
                                          homepage='https://github.com/ibus/ibus/wiki',
                                          command_line='',
                                          textdomain='ibus-anthy')
        if PY3K:
            symbol = chr(0x3042)
        else:
            symbol = unichr(0x3042)
        desc = IBus.EngineDesc(name='testanthy',
                                 longname='TestAnthy',
                                 description='Test Anthy Input Method',
                                 language='ja',
                                 license='GPL',
                                 author='Takao Fujiwara <takao.fujiwara1@gmail.com>',
                                 icon='ibus-anthy',
                                 symbol=symbol,
                                 )
        self.__component.add_engine(desc)
        self.__bus.register_component(self.__component)
        self.__bus.request_name('org.freedesktop.IBus.Anthy.Test', 0)
        return True

    def create_window(self):
        match Gtk.MAJOR_VERSION:
            case 4:
                self.create_window_gtk4()
            case 3:
                self.create_window_gtk3()
            case _:
                self.gtk_version_exception()

    def create_window_gtk4(self):
        window = Gtk.Window()
        self.__entry = entry = Gtk.Entry()
        window.connect('destroy', self.__window_destroy_cb)
        entry.connect('map', self.__entry_map_cb)
        controller = Gtk.EventControllerFocus()
        controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        controller.connect_after('enter', self.__controller_enter_cb)
        text = entry.get_delegate()
        text.add_controller(controller)
        text.connect('preedit-changed', self.__entry_preedit_changed_cb)
        buffer = entry.get_buffer()
        buffer.connect('inserted-text', self.__buffer_inserted_text_cb)
        window.set_child(entry)
        window.set_focus(entry)
        window.present()
        printflush('## Build GTK4 window')

    def create_window_gtk3(self):
        window = Gtk.Window(type = Gtk.WindowType.TOPLEVEL)
        self.__entry = entry = Gtk.Entry()
        window.connect('destroy', self.__window_destroy_cb)
        entry.connect('map', self.__entry_map_cb)
        entry.connect('focus-in-event', self.__entry_focus_in_event_cb)
        entry.connect('preedit-changed', self.__entry_preedit_changed_cb)
        buffer = entry.get_buffer()
        buffer.connect('inserted-text', self.__buffer_inserted_text_cb)
        window.add(entry)
        window.show_all()
        printflush('## Build GTK3 window')

    def gtk_version_exception(self):
        raise Exception("GTK version %d is not supported" %  Gtk.MAJOR_VERSION)

    def is_integrated_desktop(self):
        session_name = None
        if 'XDG_SESSION_DESKTOP' in os.environ:
            session_name = os.environ['XDG_SESSION_DESKTOP']
        if session_name == None:
            return False
        if len(session_name) >= 4 and session_name[0:5] == 'gnome':
            return True
        return False

    def __name_owner_changed_cb(self, connection, sender_name, object_path,
                                interface_name, signal_name, parameters,
                                user_data):
        if signal_name == 'NameOwnerChanged':
            try:
                import engine
            except ModuleNotFoundError as e:
                with self.subTest(i = 'name-owner-changed'):
                    self.fail('NG: Not installed ibus-anthy %s' % str(e))
                self.__window_destroy_cb()
                return
            engine.Engine.CONFIG_RELOADED()

    def __create_engine_cb(self, factory, engine_name):
        if engine_name == 'testanthy':
            printflush('## Creating engine')
            try:
                import engine
            except ModuleNotFoundError as e:
                with self.subTest(i = 'create-engine'):
                    self.fail('NG: Not installed ibus-anthy %s' % str(e))
                self.__window_destroy_cb()
                return
            self.__id += 1
            self.__engine = engine.Engine(self.__bus, '%s/%d' % (self.ENGINE_PATH, self.__id))
            if hasattr(self.__engine.props, 'has_focus_id'):
                self.__engine.connect('focus-in-id', self.__engine_focus_in)
                self.__engine.connect('focus-out-id', self.__engine_focus_out)
            # The timing of D-Bus signal of Engine.has_focus_id can cause
            # some 'focus-in' signals earlier and 'focus-in-id' signals later.
            self.__engine.connect('focus-in', self.__engine_focus_in)
            self.__engine.connect('focus-out', self.__engine_focus_out)
            return self.__engine

    def __engine_focus_in(self, engine, object_path=None, client=None):
        printflush('## Focus in engine %s %s' % (object_path, client))
        if self.__test_index == len(TestCases['tests']):
            if DONE_EXIT:
                self.__window_destroy_cb()
            return
        self.__engine_is_focused = True
        pass

    def __engine_focus_out(self, engine, object_path=None):
        printflush('## Focus out engine %s' % object_path)
        self.__engine_is_focused = False

    def __window_destroy_cb(self):
        match Gtk.MAJOR_VERSION:
            case 4:
                self.__list_toplevel = False
            case 3:
                Gtk.main_quit()
            case _:
                self.gtk_version_exception()

    def __entry_map_cb(self, entry):
        printflush('## Map window')

    def __controller_enter_cb(self, controller):
        if self.is_integrated_desktop():
            # Wait for 3 seconds in GNOME Wayland because there is a long time
            # lag between the "enter" signal on the event controller in GtkText
            # and the "FocusIn" D-Bus signal in BusInputContext of ibus-daemon.
            printflush('## Waiting for 3 secs')
            GLib.timeout_add_seconds(3,
                                     self.__controller_enter_delay,
                                     controller)
        else:
            printflush('## No Wait')
            GLib.idle_add(self.__controller_enter_delay,
                          controller)

    def __controller_enter_delay(self, controller):
        text = controller.get_widget()
        if not text.get_realized():
            return
        self.__entry_focus_in_event_cb(None, None)

    def __entry_focus_in_event_cb(self, entry, event):
        printflush('## Focus in entry')
        if self.__test_index == len(TestCases['tests']):
            if DONE_EXIT:
                self.__window_destroy_cb()
            return False
        self.__bus.set_global_engine_async('testanthy', -1, None, self.__set_engine_cb)
        return False

    def __idle_cb(self):
        if self.__engine_is_focused:
            self.__idle_loop.quit()
            return GLib.SOURCE_REMOVE
        elif self.__idle_count < 10:
            self.__idle_count += 1
            return GLib.SOURCE_CONTINUE
        else:
            self.__idle_loop.quit()
            return GLib.SOURCE_REMOVE

    def __set_engine_cb(self, object, res):
        printflush('## Set engine')
        if not self.__bus.set_global_engine_async_finish(res):
            with self.subTest(i = self.__test_index):
                self.fail('set engine failed: ' + error.message)
            return
        self.__enable_hiragana()
        # ibus_im_context_focus_in() is called after GlobalEngine is set.
        # The focus-in/out events happen more slowly in a busy system
        # likes with a TMT tool.
        if self.is_integrated_desktop():
            if 'IBUS_DAEMON_WITH_SYSTEMD' in os.environ and \
               os.environ['IBUS_DAEMON_WITH_SYSTEMD'] != None:
                self.__idle_loop = GLib.MainLoop(None)
                self.__idle_count = 0
                GLib.timeout_add_seconds(1, self.__idle_cb)
                self.__idle_loop.run()
        self.__main_test()

    def __get_test_condition_length(self, tag):
        tests = TestCases['tests'][self.__test_index]
        cases = tests[tag]
        type = list(cases.keys())[0]
        return len(cases[type])

    def __entry_preedit_changed_cb(self, entry, preedit_str):
        # Wait for clearing the preedit before the next __main_test() is called.
        if self.__commit_done:
            if len(preedit_str) == 0:
                self.__preedit_changes = 0
                self.__main_test()
            else:
                self.__preedit_changes += 1
            return
        if self.__is_wayland:
            # Need to fix mutter
            # GTK calls self.__entry_preedit_changed_cb() twice by the actual
            # preedit update in GNOME Wayland in case the lookup window is not
            # shown yet and the preedit is changed but not the cursor position
            # only.
            #
            # I.e. GTK receives the struct zwp_text_input_v3_listener.done()
            # from Wayland text-input protocol when the preedit is updated
            # and the "preedit-changed" signal is called at first and the
            # zwp_text_input_v3_listener.done() also calls
            # zwp_text_input_v3_commit() to notify IM changes to mutter and
            # mutter receives the struct
            # zwp_text_input_v3_interface.commit_state() from Wayland text-input
            # protocol and it causes the zwp_text_input_v3_listener.done() and
            # the "preedit-changed" signal in GTK.
            if self.__preedit_changes < 1 and self.__conversion_spaces < 2 \
               and self.__preedit_prev != preedit_str:
                self.__preedit_changes += 1
                return
            else:
                self.__preedit_changes = 0
        if self.__test_index == len(TestCases['tests']):
            if DONE_EXIT:
                self.__window_destroy_cb()
            return
        self.__preedit_prev = preedit_str
        conversion_length = self.__get_test_condition_length('conversion')
        if self.__conversion_index < conversion_length:
            self.__run_cases('conversion',
                             self.__conversion_index,
                             self.__conversion_index + 1)
            self.__conversion_index += 1
            return
        self.__run_cases('commit')

    def __enable_hiragana(self):
        settings = Gio.Settings(
                schema = "org.freedesktop.ibus.engine.anthy.common");
        result = settings.get_int('input-mode')
        if result != 0:
            printflush('## Enable hiragana %d' % result)
            key = TestCases['init']
            self.__typing(key[0], key[1], key[2])
        else:
            printflush('## Already hiragana')

    def __main_test(self):
        printflush('## Run case %d' % self.__test_index)
        self.__preedit_prev = None
        self.__conversion_index = 0
        self.__conversion_spaces = 0
        self.__commit_done = False
        self.__run_cases('preedit')

    def __run_cases(self, tag, start=-1, end=-1):
        tests = TestCases['tests'][self.__test_index]
        if tests == None:
            return
        cases = tests[tag]
        type = list(cases.keys())[0]
        i = 0
        if type == 'string':
            printflush('test step: %s sequences: "%s"' \
                       % (tag, str(cases['string'])))
            for a in cases['string']:
                if start >= 0 and i < start:
                    i += 1
                    continue
                if end >= 0 and i >= end:
                    break;
                self.__typing(ord(a), 0, 0)
                i += 1
        if type == 'keys':
            if start == -1 and end == -1:
                printflush('test step: %s sequences: %s' \
                           % (tag, str(cases['keys'])))
            for key in cases['keys']:
                if start >= 0 and i < start:
                    i += 1
                    continue
                if end >= 0 and i >= end:
                    break;
                if start != -1 or end != -1:
                    printflush('test step: %s sequences: [0x%X, 0x%X, 0x%X]' \
                               % (tag, key[0], key[1],  key[2]))
                # Check if the lookup table is shown.
                if tag == 'conversion' and \
                   (key[0] == IBus.KEY_Tab or key[0] == IBus.KEY_space):
                    self.__conversion_spaces += 1
                self.__typing(key[0], key[1], key[2])
                i += 1

    def __typing(self, keyval, keycode, modifiers):
        self.__engine.emit('process-key-event', keyval, keycode, modifiers)
        modifiers |= IBus.ModifierType.RELEASE_MASK;
        self.__engine.emit('process-key-event', keyval, keycode, modifiers)

    def __buffer_inserted_text_cb(self, buffer, position, chars, nchars):
        tests = TestCases['tests'][self.__test_index]
        cases = tests['result']
        if cases['string'] == chars:
            printflush('OK: %d %s' % (self.__test_index, chars))
        else:
            with self.subTest(i = self.__test_index):
                self.fail('NG: %d %s %s' \
                          % (self.__test_index, str(cases['string']), chars))
            if DONE_EXIT:
                self.__window_destroy_cb()
        self.__test_index += 1
        if self.__test_index == len(TestCases['tests']):
            if DONE_EXIT:
                self.__window_destroy_cb()
            return
        self.__entry.set_text('')
        # ibus-anthy updates preedit after commits the text.
        self.__commit_done = True

    def main(self):
        match Gtk.MAJOR_VERSION:
            case 4:
                while self.__list_toplevel:
                    GLib.MainContext.default().iteration(True)
            case 3:
                Gtk.main()
            case _:
                self.gtk_version_exception()

    def test_typing(self):
        if not self.register_ibus_engine():
            sys.exit(-1)
        self.__list_toplevel = True
        self.create_window()
        self.main()

def print_help(out, v = 0):
    print('-e, --exit             Exit this program after test is done.',
          file=out)
    print('-f, --force            Run this program forcibly with .anthy.',
          file=out)
    print('-h, --help             show this message.', file=out)
    print('\nenvironment variables:', file=out)
    print('IBUS_ANTHY_ENGINE_PATH Indicates the path which includes ' \
          'engine.py. the default is /usr/share/ibus-anthy/engine', file=out)
    print('IBUS_ANTHY_SETUP_PATH  Indicates the path which includes ' \
          'prefs.py. the default is /usr/share/ibus-anthy/setup', file=out)
    sys.exit(v)

def get_userhome():
    if 'HOME' not in os.environ:
        import pwd
        userhome = pwd.getpwuid(os.getuid()).pw_dir
    else:
        userhome = os.environ['HOME']
    userhome = userhome.rstrip('/')
    return userhome

def main():
    force_run = False
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keep', action='store_true',
                        help='keep this GtkWindow after test is done')
    parser.add_argument('-f', '--force', action='store_true',
                        help='run this program forcibly with .anthy')
    parser.add_argument('-t', '--tap', action='store_true',
                        help='enable TAP')
    parser.add_argument('-F', '--unittest-failfast', action='store_true',
                        help='stop on first fail or error in unittest')
    parser.add_argument('-H', '--unittest-help', action='store_true',
                        help='show unittest help message and exit')
    args, unittest_args = parser.parse_known_args()
    sys.argv[1:] = unittest_args
    if args.keep:
        global DONE_EXIT
        DONE_EXIT = False
    if args.force:
        force_run = True
    if args.unittest_failfast:
        sys.argv.append('-f')
    if args.unittest_help:
        sys.argv.append('-h')
        unittest.main()

    for anthy_config in ['/.config/anthy', '/.anthy']:
        anthy_user_dir = get_userhome() + anthy_config
        anthy_last_file = anthy_user_dir + '/last-record2_default.utf8'
        if os.path.exists(anthy_last_file) and not force_run:
            print('Please remove %s before the test' % anthy_last_file,
                  file=sys.stderr)
            sys.exit(-1)

    if args.tap:
        loader = unittest.TestLoader()
        if tap_module == TAP_MODULE_PYCOTAP:
            # Log should be in stderr instead of StringIO
            runner = TAPTestRunner(test_output_log=LogMode.LogToError)
        else:
            runner = TAPTestRunner()
        if tap_module == TAP_MODULE_TAPPY:
            runner.set_stream(True)
        unittest.main(testRunner=runner, testLoader=loader)
    else:
        unittest.main()

if __name__ == '__main__':
    main()
