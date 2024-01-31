#!/bin/sh
# vim:set noet ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2018 Takao Fujiwara <takao.fujiwara1@gmail.com>
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

# This test runs /usr/share/ibus-anthy/engine/engine.py after install anthy

PROGNAME=`basename $0`;
VERSION=0.1;
DISPLAY=:99.0;
BUILDDIR=".";
SRCDIR=".";
HAVE_GRAPHICS=1;
DESKTOP_COMMAND="gnome-session";
PYTHON="python3";
PID_XORG=0;
PID_GNOME_SESSION=0;
FORCE_TEST="";
RUN_ARGS="--exit";
# Fedora 39 Docker does not provide USER
USER=${USER:-`id | sed -e "s/uid=[0-9]*(\([^)]*\)).*/\1/"`};

usage()
{
    echo -e \
"This test runs /usr/share/ibus-anthy/engine/engine.py after install anthy\n"  \
"$PROGNAME [OPTIONS…]\n"                                                       \
"\n"                                                                           \
"OPTIONS:\n"                                                                   \
"-h, --help                       This help\n"                                 \
"-v, --version                    Show version\n"                              \
"-b, --builddir=BUILDDIR          Set the BUILDDIR\n"                          \
"-s, --srcdir=SOURCEDIR           Set the SOURCEDIR\n"                         \
"-c, --no-graphics                Use Xvfb instead of Xorg\n"                  \
"-p, --python=PATH                Use the PATH of python2 or python3\n"        \
"-d, --desktop=DESKTOP            Run DESTKTOP. The default is gnome-session\n"\
"-f, --force                      Run test suite forcibly\n"                   \
""
}

parse_args()
{
    # This is GNU getopt. "sudo port getopt" in BSD?
    ARGS=`getopt -o hvb:s:cp:d:f --long help,version,builddir:,srcdir:,no-graphics,python:,desktop:,force \
        -- "$@"`;
    eval set -- "$ARGS"
    while [ 1 ] ; do
        case "$1" in
        -h | --help )        usage; exit 0;;
        -v | --version )     echo -e "$VERSION"; exit 0;;
        -b | --builddir )    BUILDDIR="$2"; shift 2;;
        -s | --srcdir )      SRCDIR="$2"; shift 2;;
        -c | --no-graphics ) HAVE_GRAPHICS=0; shift;;
        -p | --python )      PYTHON="$2"; shift 2;;
        -d | --desktop )     DESKTOP_COMMAND="$2"; shift 2;;
        -f | --force )       FORCE_TEST="1"; shift;;
        -- )                 shift; break;;
        * )                  usage; exit 1;;
        esac;
    done;
}

init_desktop()
{
    if test x$FORCE_TEST != x ; then
        RUN_ARGS="$RUN_ARGS --force";
    fi;

    if test ! -f $HOME/.config/gnome-initial-setup-done ; then
        if test ! -f /var/lib/AccountsService/users/$USER ; then
            mkdir -p /var/lib/AccountsService/users
            cat >> /var/lib/AccountsService/users/$USER << _EOF
[User]
Language=ja_JP.UTF-8
XSession=gnome
SystemAccount=false
_EOF
        fi
        mkdir -p $HOME/.config
        touch $HOME/.config/gnome-initial-setup-done
    fi

    # Prevent from launching a XDG dialog
    XDG_LOCALE_FILE="$HOME/.config/user-dirs.locale"
    if test -f $XDG_LOCALE_FILE ; then
        XDG_LANG_ORIG=`cat $XDG_LOCALE_FILE`
        XDG_LANG_NEW=`echo $LANG | sed -e 's/\(.*\)\..*/\1/'`
        if [ "$XDG_LANG_ORIG" != "$XDG_LANG_NEW" ] ; then
            echo "Overriding XDG locale $XDG_LANG_ORIG with $XDG_LANG_NEW"
            echo "$XDG_LANG_NEW" > $XDG_LOCALE_FILE
        fi
    fi
}

run_dbus_daemon()
{
    a=`ps -ef | grep dbus-daemon | grep "\-\-system" | grep -v session | grep -v grep`
    if test x"$a" = x ; then
        eval `dbus-launch --sh-syntax`
    fi
    SUSER=`echo "$USER" | cut -c 1-7`;
    a=`ps -ef | grep dbus-daemon | grep "$SUSER" | grep -v gdm | grep session | grep -v grep`
    if test x"$a" = x ; then
        systemctl --user start dbus
        export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$UID/bus
    fi
    systemctl --user status dbus | col -b
    ps -ef | grep dbus-daemon | grep "$SUSER" | grep -v gdm | egrep 'session|system' | grep -v grep
    systemctl --user show-environment | col -b
}

run_desktop()
{
    if test $HAVE_GRAPHICS -eq 1 ; then
        /usr/libexec/Xorg.wrap -noreset +extension GLX +extension RANDR +extension RENDER -logfile ./xorg.log -config ./xorg.conf -configdir . $DISPLAY &
    else
        /usr/bin/Xvfb $DISPLAY -noreset +extension GLX +extension RANDR +extension RENDER -screen 0 1280x1024x24 &
    fi;
    PID_XORG=$!;
    sleep 1;
    export DISPLAY=$DISPLAY;
    $DESKTOP_COMMAND &
    PID_GNOME_SESSION=$!;
    sleep 30;
    if test "$DESKTOP_COMMAND" != "gnome-session" ; then
        ibus-daemon --daemonize --verbose;
        sleep 1;
    fi
}

run_test_suite()
{
    rm -rf $HOME/.anthy;
    rm -rf $HOME/.config/anthy;
    cd `dirname $0`;

    echo "#### Starting $PYTHON API test $RUN_ARGS";
    export GTK_IM_MODULE=ibus
    $PYTHON -u $SRCDIR/anthytest.py $RUN_ARGS;
    RETVAL=$?
    # Return 5 with "NO TESTS RAN" in unittest/runner.py since python 3.12.1
    if test $RETVAL -ne 0 && test $RETVAL -ne 5; then
        exit 1;
    fi;
    if test x$FORCE_TEST = x ; then
        for ANTHY_CONFIG in ".anthy" ".config/anthy" ; do
            if test -d $HOME/$ANTHY_CONFIG ; then
                rm -r $HOME/$ANTHY_CONFIG;
            fi;
        done;
    fi;
}

finit()
{
    if "test $DESKTOP_COMMAND" != "gnome-session" ; then
        ibus exit;
    fi;
    kill $PID_GNOME_SESSION $PID_XORG;
}

main()
{
    parse_args $@;
    init_desktop;
    run_dbus_daemon;
    run_desktop;
    run_test_suite;
    finit;
}

main $@;
