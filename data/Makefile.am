# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2010-2026 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2010-2018 Red Hat, Inc.
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

noinst_DATA = era.stamp

dicts_DATA = \
	emoji.t \
	era.t \
	oldchar.t \
	symbol.t \
	$(NULL)

dictsdir = $(pkgdatadir)/dicts

# rf. i18n metainfo.xml
# http://www.freedesktop.org/software/appstream/docs/sect-Quickstart-Translation.html
# https://blogs.gnome.org/hughsie/2016/01/25/appdata-and-the-gettext-domain/
metainfo_in_files = ibus-anthy.appdata.xml.in
metainfo_DATA = org.freedesktop.ibus.engine.anthy.metainfo.xml
metainfodir=$(datadir)/metainfo

schemas_in_files = org.freedesktop.ibus.engine.anthy.gschema.xml.in
schemas_DATA = $(schemas_in_files:.xml.in=.xml)
schemasdir = $(datadir)/glib-2.0/schemas

CLEANFILES = \
        $(metainfo_DATA) \
        $(schemas_DATA) \
        emoji.t \
        era.stamp \
        $(NULL)

$(metainfo_DATA): $(metainfo_in_files) Makefile
	$(AM_V_GEN)$(MSGFMT) --xml --template $< -d $(top_srcdir)/po -o $@

$(schemas_DATA): $(schemas_in_files)
	KASUMI_EXEC_BASENAME=`basename $(KASUMI_EXEC_FILE)`; \
	$(SED) -e "s|\@ANTHY_ZIPCODE_FILE\@|$(ANTHY_ZIPCODE_FILE)|g" \
	       -e "s|\@KASUMI_EXEC_FILE\@|$(KASUMI_EXEC_FILE)|g" \
	       -e "s|\@KASUMI_EXEC_BASENAME\@|$$KASUMI_EXEC_BASENAME|g" \
	       -e "s|\@KASUMI_ICON_FILE\@|$(KASUMI_ICON_FILE)|g" \
	       -e "s|\@ON_OFF_KEYS\@|$(ON_OFF_KEYS)|g" \
	       -e "s|\@pkgdatadir\@|$(pkgdatadir)|g" \
	$< > $@


emoji.t: emoji-each.t emoji-emoji.t
	@echo "Generate $@"; \
	$(SED) -e '/^#/d' $(srcdir)/emoji-emoji.t > emoji-emoji.t.$$$$; \
	$(SED) -e "/^#@EMOJI_EMOJI@/r emoji-emoji.t.$$$$" \
	        $(srcdir)/emoji-each.t > emoji-each.t.$$$$; \
	$(SED) -e '/^#@EMOJI_EMOJI@/d' emoji-each.t.$$$$ > emoji.t; \
	rm emoji-emoji.t.$$$$ emoji-each.t.$$$$; \
	$(NULL)

if ENABLE_ZIPCODE
dicts_DATA += zipcode.t

zipcode.t: $(ANTHY_ZIPCODE_FILE)
	@echo "Generate $@"; \
	$(PYTHON) zipcode-textdic.py $<; \
	$(NULL)

CLEANFILES += zipcode.t
endif

era.t: era.stamp

era.stamp:
	make_era_t=0; \
	if test -f $(srcdir)/era.t ; then \
	    if ! $(PYTHON) $(srcdir)/era.py --check $(srcdir)/era.t ; then \
	        rm $(srcdir)/era.t; \
	        make_era_t=1; \
	    fi; \
	else \
	    make_era_t=1; \
	fi; \
	if test $$make_era_t -eq 1 ; then \
	    if ! $(PYTHON) $(srcdir)/era.py $(srcdir)/era.t.in \
	        --output $(builddir)/era.t ; then \
	        exit 1; \
	    fi; \
	    echo "Generate era.t"; \
	fi; \
	touch era.stampT; \
	mv era.stampT era.stamp;

check:
	file=$(builddir)/era.t; \
	test -f "$$file" || file=$(srcdir)/era.t; \
	$(PYTHON) $(srcdir)/era.py --check "$$file";

install-data-hook:
	if test -z "$(DESTDIR)"; then \
	    glib-compile-schemas $(schemasdir); \
	fi

uninstall-hook:
	SCHEMAS_FILES=`ls $(schemasdir)/*.gschema.xml` || true;         \
	if test -z "$$SCHEMAS_FILES" &&                                 \
	   test -f $(schemasdir)/gschemas.compiled; then                \
	    rm $(schemasdir)/gschemas.compiled;                         \
	fi

EXTRA_DIST = \
        $(metainfo_in_files) \
        $(schemas_in_files) \
        emoji-each.t \
        emoji-emoji.t \
        era.t \
        era.t.in \
        era.py \
        oldchar.t \
        symbol.t \
        zipcode-textdic.py \
        $(NULL)
