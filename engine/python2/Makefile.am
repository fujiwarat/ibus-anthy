# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2019 Takao Fujiwara <takao.fujiwara1@gmail.com>
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

BUILT_SOURCES = _config.py

engine_anthy_PYTHON = \
	_config.py \
	engine.py \
	factory.py \
	jastring.py \
	kana.py \
	main.py \
	romaji.py \
	segment.py \
	tables.py \
	thumb.py \
	$(NULL)
engine_anthydir = $(pkgdatadir)/engine
engine_anthy_built_files = $(BUILT_SOURCES)
engine_anthy_built_in_files = $(addsuffix .in, $(engine_anthy_built_files))

PYGTK2_ANTHY_RAW = anthy.i
PYGTK2_ANTHY_GEN = anthy.py anthy_wrap.c

if HAVE_PYGTK2_ANTHY
anthy_DATA = \
	anthy.py \
	$(NULL)
anthy_LTLIBRARIES = _anthy.la
anthydir = @pyexecdir@

_anthy_la_SOURCES = \
	$(NULL)

nodist__anthy_la_SOURCES = \
	anthy_wrap.c \
	$(NULL)

_anthy_la_CFLAGS = \
	@ANTHY_CFLAGS@ \
	@PYTHON_CFLAGS@ \
	$(NULL)

_anthy_la_LDFLAGS = \
	@ANTHY_LIBS@ \
	@PYTHON_LIBS@ \
	-avoid-version \
	-module \
	$(NULL)

anthy.py anthy_wrap.c: anthy.i
	$(SWIG) -python $(ANTHY_CFLAGS) -I/usr/include -o anthy_wrap.c $(srcdir)/anthy.i
endif

libexec_SCRIPTS = ibus-engine-anthy
component_DATA = anthy.xml
componentdir = $(datadir)/ibus/component
engine_DATA = default.xml
enginedir = $(pkgdatadir)/engine

# $(SYMBOL_XML) cannot be extracted in Makefile but $(libexecdir) can be
# extracted to ${exec_prefix}/libexec so use capital @LIBEXECDIR@ here.
%.xml: %.inputMethod.xml.in
	sed -e "s|\@LIBEXECDIR\@|$(libexecdir)|g" \
	    -e "s|\@PKGDATADIR\@|$(pkgdatadir)|g" \
	$< > $@

ibus-engine-anthy: ibus-engine-anthy.in
	sed -e "s|\@prefix\@|$(prefix)|g" \
	    -e "s|\@exec_prefix\@|$(exec_prefix)|g" \
	    -e "s|\@libexecdir\@|$(libexecdir)|g" \
	    -e "s|\@datarootdir\@|$(datarootdir)|g" \
	    -e "s|\@PACKAGE\@|$(PACKAGE)|g" \
	    -e "s|\@PYTHON\@|$(PYTHON)|g" \
	    -e "s|\@ENV_IBUS_ENGINE\@|$(ENV_IBUS_ENGINE)|g" \
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

test:
	$(ENV_IBUS_TEST) \
		DBUS_DEBUG=true \
		IBUS_ANTHY_PKGDATADIR=$(abs_top_srcdir) \
		PYTHONPATH=$(builddir)/.libs:@pyexecdir@ \
		$(PYTHON) \
		$(srcdir)/main.py

EXTRA_DIST = \
	$(engine_anthy_built_in_files) \
	$(PYGTK2_ANTHY_RAW) \
	anthy.inputMethod.xml.in.in \
	default.inputMethod.xml.in.in \
	ibus-engine-anthy.in \
	$(NULL)

CLEANFILES = \
	$(BUILT_SOURCES) \
	$(PYGTK2_ANTHY_GEN) \
	anthy.xml \
	default.xml \
	ibus-engine-anthy \
	*.pyc \
	$(NULL)

DISTCLEANFILES = \
	anthy.inputMethod.xml.in \
	default.inputMethod.xml.in \
	$(NULL)

# Need a time lag between .py and .py.in files to build .py files
# because *_PYTHON valuables are installed in the tarball.
dist-hook:
	@sleep 1; \
	for in_file in $(engine_anthy_built_in_files) ; do \
	    if [ -f $(distdir)/$(srcdir)/$$in_file ] ; then \
	        touch $(distdir)/$(srcdir)/$$in_file; \
	    fi; \
	done;

