# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2017-2021 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2017-2019 Red Hat, Inc.
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


CLEANFILES =

check:
	bash -x $(srcdir)/test-build.sh --builddir=$(builddir) --srcdir=$(srcdir)

if ENABLE_INSTALLED_TESTS
test_execsdir = $(libexecdir)/installed-tests/ibus-anthy
test_execs = anthytest
test_execs_SCRIPTS = \
    anthycases.py \
    anthytest.py \
    $(NULL)

test_metas_in = meta.test.in
test_metas = $(addsuffix .test, $(test_execs))
test_sources_DATA = \
    $(test_metas) \
    $(NULL)
test_sourcesdir = $(datadir)/installed-tests/ibus-anthy

CLEANFILES += \
    $(test_metas) \
    $(NULL)
endif

$(test_metas): $(test_metas_in)
	f=`echo $@ | sed -e 's/\.test//'`; \
	TEST_EXEC=$(test_execsdir)/$${f}.py; \
	sed -e "s|@TEST_EXEC[@]|$$TEST_EXEC|g" $(test_metas_in) > $@.tmp; \
	mv $@.tmp $@; \
	$(NULL)

EXTRA_DIST = \
    anthycases.py \
    anthytest.py \
    foo.py \
    meta.test.in \
    test-build.sh \
    test-console.sh \
    $(NULL)
