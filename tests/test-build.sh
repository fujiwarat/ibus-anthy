#!/bin/sh
# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2018-2021 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2018 Red Hat, Inc.
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

# This test runs $(top_builddir)/engine/python*/engine.py before install anthy

BUILDDIR=".";
SRCDIR=".";
ANTHY_SCHEMA_FILE=org.freedesktop.ibus.engine.anthy.gschema.xml;
SCHEMA_TMPDIR="";
FORCE_TEST="";
RUN_ARGS="";

usage()
{
    echo -e \
"This test runs top_builddir/engine/python*/engine.py before install anthy\n"  \
"$PROGNAME [OPTIONS…]\n"                                                       \
"\n"                                                                           \
"OPTIONS:\n"                                                                   \
"-h, --help                       This help\n"                                 \
"-v, --version                    Show version\n"                              \
"-b, --builddir=BUILDDIR          Set the BUILDDIR\n"                          \
"-s, --srcdir=SOURCEDIR           Set the SOURCEDIR\n"                         \
"-f, --force                      Run test suite forcibly\n"                   \
""
}

parse_args()
{
    # This is GNU getopt. "sudo port getopt" in BSD?
    ARGS=`getopt -o hvb:s: --long help,version,builddir:,srcdir: \
        -- "$@"`;
    eval set -- "$ARGS"
    while [ 1 ] ; do
        case "$1" in
        -h | --help )        usage; exit 0;;
        -v | --version )     echo -e "$VERSION"; exit 0;;
        -b | --builddir )    BUILDDIR="$2"; shift 2;;
        -s | --srcdir )      SRCDIR="$2"; shift 2;;
        -f | --force )       FORCE_TEST="1"; shift;;
        -- )                 shift; break;; 
        * )                  usage; exit 1;;
        esac;
    done;
}

maybe_install_pycotap() {
    # Red Hat specific hint.
    if test -f /etc/redhat-release ; then
        if ! rpm -q --quiet python3-pycotap; then
            echo "Please install python3-pycotap"
            exit -1
        fi
    fi;

    # Check if pycotap is already available.
    if ! python3 -c "import pycotap"; then
        PIP=pip3
        if ! command -v $PIP &> /dev/null ; then
            PIP=pip
        fi
        echo "pycotap not found; installing via $PIP"
        if ! $PIP install pycotap --user; then
            echo "failed to install pycotap"
            exit -1
        fi
    fi
}

init_environment()
{
    if test x$FORCE_TEST != x ; then
        RUN_ARGS="$RUN_ARGS --force";
    fi;

    maybe_install_pycotap

    if test ! -f $BUILDDIR/../data/$ANTHY_SCHEMA_FILE ; then
        echo "Not found $BUILDDIR/../data/$ANTHY_SCHEMA_FILE";
        exit -1;
    fi;
    SCHEMA_TMPDIR=`mktemp -d`;
    if test $? -ne 0 ; then
        echo "FAILED mktemp";
        exit -1;
    fi;
    cp $BUILDDIR/../data/$ANTHY_SCHEMA_FILE $SCHEMA_TMPDIR;
    glib-compile-schemas $SCHEMA_TMPDIR;
    if test $? -ne 0 ; then
        echo "FAILED glib-compile-schemas $SCHEMA_TMPDIR";
        exit -1;
    fi;
    if test ! -f $SCHEMA_TMPDIR/gschemas.compiled ; then
        echo "Not found $SCHEMA_TMPDIR/gschemas.compiled";
        exit -1;
    fi;
    ls $BUILDDIR/../gir/Anthy*.typelib > /dev/null;
    if test $? -ne 0 ; then
        echo "Not found $BUILDDIR/../gir/Anthy*.typelib";
        exit -1;
    fi;
}

run_ibus_daemon()
{
    ibus-daemon --daemonize --verbose --panel disable;
    sleep 1;
    USER=`echo "$USER" | cut -c 1-7`;
    ps -ef | grep "$SUSER" | grep ibus | grep -v grep;
}

run_test_suite()
{
    export GSETTINGS_SCHEMA_DIR=$SCHEMA_TMPDIR;
    export GI_TYPELIB_PATH=$BUILDDIR/../gir;
    LD_LIBRARY_PATH=$BUILDDIR/../gir/.libs;
    export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$BUILDDIR/../gir;
    export GTK_IM_MODULE=ibus;

    for i in 3; do
        echo "#### Starting Python$i API test $RUN_ARGS";
        env IBUS_ANTHY_ENGINE_PATH=$SRCDIR/../engine/python$i          \
            IBUS_ANTHY_SETUP_PATH=$SRCDIR/../setup/python$i            \
        python$i -u $SRCDIR/anthytest.py $RUN_ARGS;
        if test $? -ne 0 ; then
            exit -1;
        fi;
        if test x$FORCE_TEST = x ; then
            rm -r $HOME/.anthy;
            rm -r $HOME/.config/anthy;
        fi;
    done;
}

finit()
{
    rm -rf $SCHEMA_TMPDIR;
    ibus exit;
}

main()
{
    parse_args $@;
    init_environment;
    run_ibus_daemon;
    run_test_suite;
    finit;
}

main $@;
