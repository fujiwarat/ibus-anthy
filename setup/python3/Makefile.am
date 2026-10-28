# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
# Copyright (c) 2010-2021 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2017 Red Hat, Inc.
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

desktop_in_in_files = ibus-setup-anthy.desktop.in.in
desktop_in_files = $(desktop_in_in_files:.in.in=.in)

$(desktop_in_files): %.desktop.in: %.desktop.in.in Makefile
	$(AM_V_GEN) sed \
	       -e "s|\@libexecdir\@|$(libexecdir)|" \
	       -e "s|\@pkgdatadir\@|$(pkgdatadir)|" \
	       $< > $@.tmp && mv $@.tmp $@

desktopdir=$(datadir)/applications
desktop_DATA = ibus-setup-anthy.desktop

$(desktop_DATA): $(desktop_in_files) Makefile
	$(AM_V_GEN)$(MSGFMT) --desktop --template $< -d $(top_srcdir)/po -o $@

BUILT_SOURCES = \
	_config.py \
	$(NULL)

libexec_SCRIPTS = ibus-setup-anthy

setup_anthy_PYTHON = \
	_config.py \
	anthyprefs.py \
	main.py \
	prefs.py \
	setup.ui \
	$(NULL)

setup_anthy_built_files = \
	$(BUILT_SOURCES) \
	$(libexec_SCRIPTS) \
	$(NULL)

setup_anthy_built_in_files = $(addsuffix .in, $(setup_anthy_built_files))

setup_anthydir = $(datadir)/ibus-anthy/setup

CONFIG_CLEAN_FILES = \
	$(BUILT_SOURCES) \
	$(NULL)

CLEANFILES = \
	$(BUILT_SOURCES) \
	$(desktop_DATA) \
	$(desktop_in_files) \
	$(libexec_SCRIPTS) \
	*.pyc \
	$(NULL)

EXTRA_DIST = \
	$(desktop_in_in_files) \
	$(setup_anthy_built_in_files) \
	$(NULL)

ibus-setup-anthy: ibus-setup-anthy.in
	sed -e "s|\@datadir\@|$(datadir)|g" \
	    -e "s|\@localedir\@|$(localedir)|g" \
	    -e "s|\@PACKAGE\@|$(PACKAGE)|g" \
	    -e "s|\@PYTHON\@|$(PYTHON)|g" \
	$< > $@

_config.py: _config.py.in
	sed -e "s|\@pkgdatadir\@|$(pkgdatadir)|g" \
	    -e "s|\@libexecdir\@|$(libexecdir)|g" \
	    -e "s|\@datadir\@|$(datadir)|g" \
	    -e "s|\@ANTHY_PC\@|$(ANTHY_PC)|g" \
	    -e "s|\@LAYOUT\@|$(LAYOUT)|g" \
	    -e "s|\@SYMBOL_CHAR_INT\@|$(SYMBOL_CHAR_INT)|g" \
	    -e "s|\@ICON_PREFERENCE\@|$(ICON_PREFERENCE)|g" \
	    -e "s|\@VERSION\@|$(VERSION)|g" \
	$< > $@

# Need a time lag between .py and .py.in files to build .py files
# because *_PYTHON valuables are installed in the tarball.
dist-hook:
	@sleep 1; \
	for in_file in $(setup_anthy_built_in_files) ; do \
	    if [ -f $(distdir)/$(srcdir)/$$in_file ] ; then \
	        touch $(distdir)/$(srcdir)/$$in_file; \
	    fi; \
	done;

test:
	$(ENV_IBUS_TEST) DBUS_DEBUG=true \
		   LANG=en_US \
		   PYTHONPATH=$(abs_top_srcdir):$(pyexecdir) \
		   IBUS_LOCALEDIR=@localedir@ \
		   $(PYTHON) $(srcdir)/main.py

