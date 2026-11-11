# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2012-2019 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2012 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2012-2013 Red Hat, Inc.
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

INTROSPECTION_GIRS =

libanthygobject = libanthygobject-1.0.la

AM_CPPFLAGS = \
	@GOBJECT2_CFLAGS@ \
	@ANTHY_CFLAGS@ \
	$(NULL)

libanthygobject_LTLIBRARIES = $(libanthygobject)
libanthygobjectdir = @ANTHY_GOBJECT_LIBDIR@

libanthygobject_1_0_la_SOURCES = \
	anthygcontext.c \
	$(NULL)

libanthygobject_1_0_la_LIBADD = \
	@GOBJECT2_LIBS@ \
	@ANTHY_LIBS@ \
	$(NULL)

libanthygobject_1_0_la_LDFLAGS = \
	-no-undefined                           \
	-export-symbols-regex "anthy_.*"        \
	-version-info @LT_VERSION_INFO@         \
	$(NULL)

ANTHY_INCLUDEDIR = $(shell pkg-config --variable=includedir $(ANTHY_PC))

anthyincludedir = $(includedir)/ibus-anthy-1.0
anthyinclude_HEADERS = \
	anthygcontext.h \
	$(NULL)

# gobject introspection
-include $(INTROSPECTION_MAKEFILE)

Anthy-9000.gir: $(libanthygobject) Makefile
Anthy_9000_gir_SCANNERFLAGS = \
	--pkg=$(ANTHY_PC) \
	--external-library \
	--reparse-validate \
	--identifier-prefix=Anthy \
	--symbol-prefix=anthy \
	--accept-unprefixed \
	--warn-all \
	$(NULL)
Anthy_9000_gir_INCLUDES = GObject-2.0
Anthy_9000_gir_LIBS = $(libanthygobject) $(ANTHY_PC)
Anthy_9000_gir_CFLAGS = @ANTHY_CFLAGS@
Anthy_9000_gir_FILES = \
	$(libanthygobject_1_0_la_SOURCES) \
	$(anthyinclude_HEADERS) \
	$(ANTHY_INCLUDEDIR)/anthy/anthy.h \
	$(NULL)
INTROSPECTION_GIRS += Anthy-9000.gir

girdir = @ANTHY_GOBJECT_GIRDIR@
dist_gir_DATA = $(INTROSPECTION_GIRS)

typelibsdir = @ANTHY_GOBJECT_TYPELIBSDIR@
typelibs_DATA = $(INTROSPECTION_GIRS:.gir=.typelib)

noinst_PROGRAMS = test

test_SOURCES = test.c
test_LDADD = \
	$(libanthygobject) \
	@GOBJECT2_LIBS@ \
	@ANTHY_LIBS@ \
	$(NULL)

CLEANFILES = \
	$(dist_gir_DATA) \
	$(typelibs_DATA) \
	$(NULL)

DISTCLEANFILES = \
	$(NULL)

