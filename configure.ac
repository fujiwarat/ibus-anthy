# vim:set et ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2012 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2012 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

dnl - if not 1, append datestamp to the version number.
m4_define([ibus_released], [0])
m4_define([ibus_major_version], [1])
m4_define([ibus_minor_version], [3])
m4_define([ibus_micro_version], [99])
m4_define([ibus_abi_current], [4])
m4_define([ibus_abi_revision],
          [m4_eval(100 * ibus_minor_version + ibus_micro_version)])
m4_define([ibus_abi_age], [0])
m4_define(ibus_maybe_datestamp,
    m4_esyscmd([if test x]ibus_released[ != x1; then date +.%Y%m%d | tr -d '\n\r'; fi]))

m4_define([ibus_version],
    ibus_major_version.ibus_minor_version.ibus_micro_version[]ibus_maybe_datestamp)
m4_define([glib_required_version], [2.26.0])

AC_INIT([ibus-anthy], [ibus_version], [http://code.google.com/p/ibus/issues/entry],[ibus-anthy])
AM_INIT_AUTOMAKE([1.10])
AC_GNU_SOURCE

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])

dnl - define PACKAGE_VERSION_* variables
AS_VERSION
AS_NANO
AM_SANITY_CHECK
AM_MAINTAINER_MODE
AM_DISABLE_STATIC
AC_PROG_CC
AM_PROG_CC_C_O
AC_PROG_CXX
AC_ISC_POSIX
AC_HEADER_STDC
AM_PROG_LIBTOOL
IT_PROG_INTLTOOL([0.35.0])

dnl - For dislpay Date
m4_define(ibus_datedisplay,
    m4_esyscmd(date '+%a %b %d %Y' | tr -d '\n\r'))
DATE_DISPLAY="ibus_datedisplay"
AC_SUBST(DATE_DISPLAY)

dnl - check anthy
PKG_CHECK_MODULES(ANTHY, [
    anthy
])

AC_CHECK_DECLS([
NTH_UNCONVERTED_CANDIDATE,
NTH_KATAKANA_CANDIDATE,
NTH_HIRAGANA_CANDIDATE,
NTH_HALFKANA_CANDIDATE],,
    AC_MSG_ERROR([Could not find NTH_*_CANDIDATE values in anthy.h]),
    [[#include <anthy/anthy.h>]])

PKG_CHECK_MODULES(GOBJECT2, [
    gobject-2.0 >= glib_required_version
])

dnl - GObject introspection
GOBJECT_INTROSPECTION_CHECK([0.6.8])

dnl - check libanthy directory
AC_ARG_WITH(anthygobject-libdir,
           [AC_HELP_STRING([--with-anthygobject-libdir=PATH],
                           [file path of libanthygobject.so])],
           [ANTHY_GOBJECT_LIBDIR="$withval"],
           [ANTHY_GOBJECT_LIBDIR='$(libdir)'])
AC_SUBST(ANTHY_GOBJECT_LIBDIR)

dnl - check anthygir directory
AC_ARG_WITH(anthygoject-girdir,
           [AC_HELP_STRING([--with-anthygobject-girdir=PATH],
                           [file path of anthy.gir])],
           [ANTHY_GOBJECT_GIRDIR="$withval"],
           [ANTHY_GOBJECT_GIRDIR='$(datadir)/gir-1.0'])
AC_SUBST(ANTHY_GOBJECT_GIRDIR)

dnl - check anthygir directory
AC_ARG_WITH(anthygobject-typelibsdir,
           [AC_HELP_STRING([--with-anthygobject-typelibsdir=PATH],
                           [file path of anthy.typelibs])],
           [ANTHY_GOBJECT_TYPELIBSDIR="$withval"],
           [ANTHY_GOBJECT_TYPELIBSDIR='$(libdir)/girepository-1.0'])
AC_SUBST(ANTHY_GOBJECT_TYPELIBSDIR)

dnl - check env
AC_PATH_PROG(ENV_IBUS_TEST, env)
AC_SUBST(ENV_IBUS_TEST)

dnl - check python
dnl ibus-anthy and pygobject3 uses python2
dnl but AM_PATH_PYTHON does not check if python3 is used
dnl so I created IBUS_PYTHON_CHECK_VERSION2 from AM_PYTHON_CHECK_VERSION
dnl to check both the python minimum version and 3.

dnl from python.m4
IBUS_PYTHON_MIN_VERSION=2.5
IBUS_PYTHON_CHECK_VERSION2() {
    ARGS="import sys
# split strings by '.' and convert to numeric.  Append some zeros
# because we need at least 4 digits for the hex conversion.
# map returns an iterator in Python 3.0 and a list in 2.x
minver = list(map(int, '$2'.split('.')))
if [len](minver) < 4:
    for i in list(range(0, 4 - [len](minver))): minver.append(0)
minverhex = 0
# xrange is not present in Python 3.0 and range returns an iterator
for i in list(range(0, 4)): minverhex = (minverhex << 8) + minver[[i]]
threever = [[3, 0, 0, 0]]
threeverhex = 0
for i in list(range(0, 4)): threeverhex = (threeverhex << 8) + threever[[i]]
sys.exit(not (sys.hexversion >= minverhex and \\
              sys.hexversion < threeverhex))"
    PROG="$1"
    PYTHON_VERSION2=`"$PROG" -c "import sys; sys.stdout.write(sys.version[[:3]])"`
    "$PROG" -c "$ARGS"
    return $?
}

AC_MSG_CHECKING([whether you have python2])
HAS_PYTHON2=no
IBUS_PYTHON_INTERPRETER_LIST='
python python2 python2.7 python2.6 pythhon2.5
'
for PYTHON2 in $IBUS_PYTHON_INTERPRETER_LIST ; do
    IBUS_PYTHON_CHECK_VERSION2 $PYTHON2 $IBUS_PYTHON_MIN_VERSION
    if test $? -eq 0 ; then
        HAS_PYTHON2=yes
        break
    fi
done
AC_MSG_RESULT($HAS_PYTHON2)

if test x"$HAS_PYTHON2" = xyes; then
    AC_PATH_PROG(PYTHON, $PYTHON2)
    PYTHON_VERSION=$PYTHON_VERSION2
fi

dnl export $pyexecdir using existent $PYTHON
AM_PATH_PYTHON([$IBUS_PYTHON_MIN_VERSION])

dnl - engine-env
AC_MSG_CHECKING([what are the enviroments for ibus-engine-anthy])
AC_ARG_WITH(engine-env,
           [AC_HELP_STRING([--engine-env=ENVIRONMENTS],
                           [ibus-engine-anthy environments likes
                            "LD_LIBRARY_PATH=/usr/lib/anthy" for libanthy.so.
                            default is none])],
           [engine_env="$withval"],
           [engine_env='none'])
AC_MSG_RESULT($engine_env)
ENV_IBUS_ENGINE=""
if test x"$engine_env" != xnone; then
    ENV_IBUS_ENGINE="$ENV_IBUS_TEST $engine_env"
fi
AC_SUBST(ENV_IBUS_ENGINE)

dnl - check pygtk2
AC_MSG_CHECKING([whether you enable pygtk2 anthy])
AC_ARG_ENABLE(pygtk2-anthy,
              AS_HELP_STRING([--enable-pygtk2-anthy=no/yes],
                             [Install pygtk2 anthy default=no]),
              enable_pygtk2_anthy=yes,
              enable_pygtk2_anthy=no)
AC_MSG_RESULT($enable_pygtk2_anthy)

if test x"$enable_pygtk2_anthy" = xyes; then
    AM_CONDITIONAL(HAVE_PYGTK2_ANTHY, true)

    dnl - check swig
    AC_PATH_PROG(SWIG, swig)
    if test x"$SWIG" = x""; then
        AC_MSG_ERROR([can not find swig])
    fi
    AC_SUBST(SWIG)

    AC_PATH_PROG(PYTHON_CONFIG, python$PYTHON_VERSION-config)
    if test x"$PYTHON_CONFIG" = x""; then
        AC_PATH_PROG(PYTHON_CONFIG, python-config-$PYTHON_VERSION)
    fi
    if test x"$PYTHON_CONFIG" = x""; then
        AC_PATH_PROG(PYTHON_CONFIG, python-config)
    fi
    if test x"$PYTHON_CONFIG" != x""; then
        PYTHON_CFLAGS=`$PYTHON_CONFIG --includes`
        PYTHON_LIBS=`$PYTHON_CONFIG --libs`
    else
        PYTHON_CFLAGS=`$PYTHON $srcdir/python-config.py --includes`
        PYTHON_LIBS=`$PYTHON $srcdir/python-config.py --libs`
    fi
    AC_SUBST(PYTHON_CFLAGS)
    AC_SUBST(PYTHON_LIBS)
else
    AM_CONDITIONAL(HAVE_PYGTK2_ANTHY, false)
fi


dnl - check file path of Anthy zipcode.t
AC_ARG_WITH(anthy-zipcode,
           [AC_HELP_STRING([--with-anthy-zipcode=FILE],
                           [file path of Anty zipcode.t])],
           [ANTHY_ZIPCODE_FILE="$withval"],
           [ANTHY_ZIPCODE_FILE="$datadir/anthy/zipcode.t"])
AC_SUBST(ANTHY_ZIPCODE_FILE)

dnl - check file path of kasumi bin
AC_ARG_WITH(kasumi-exec,
           [AC_HELP_STRING([--with-kasumi-exec=FILE],
                           [file path of kasumi bin])],
           [KASUMI_EXEC_FILE="$withval"],
           [KASUMI_EXEC_FILE="$bindir/kasumi"])
AC_SUBST(KASUMI_EXEC_FILE)

dnl - check file path of kasumi icon
AC_ARG_WITH(kasumi-icon,
           [AC_HELP_STRING([--with-kasumi-icon=FILE],
                           [file path of kasumi icon])],
           [KASUMI_ICON_FILE="$withval"],
           [KASUMI_ICON_FILE="$datadir/pixmaps/kasumi.png"])
AC_SUBST(KASUMI_ICON_FILE)

dnl - check hotkeys for ibus-anthy which is used for ibus bridge mode.
dnl - Normally you don't need this so could be HOTKEYS="no"
AC_ARG_WITH(hotkeys,
           [AC_HELP_STRING([--with-hotkeys=HOTKEYS],
                   [Use hotkeys for ibus bridge mode. (available value: yes/no/keys)])],
           [HOTKEYS="$withval"],
           [HOTKEYS="no"])
if test x"$HOTKEYS" = x"no"; then
    HOTKEYS_XML="<!-- <hotkeys>Control+space,Zenkaku_Hankaku</hotkeys> -->"
elif test x"$HOTKEYS" = x"yes"; then
    HOTKEYS_XML="<hotkeys>Control+space,Zenkaku_Hankaku</hotkeys>"
elif test x"$HOTKEYS" = x; then
    HOTKEYS_XML="<hotkeys>Control+space,Zenkaku_Hankaku</hotkeys>"
elif test x"$HOTKEYS" = xnull; then
    HOTKEYS_XML="<hotkeys></hotkeys>"
else
    HOTKEYS_XML="<hotkeys>${HOTKEYS}</hotkeys>"
fi
AC_SUBST(HOTKEYS_XML)

SYMBOL_CHAR='&#x3042;'
SYMBOL_TEST="from gi.repository import IBus
engine = IBus.EngineDesc(name='test')
exit(not hasattr(engine, 'get_symbol'))
"
$PYTHON -c "$SYMBOL_TEST"
if test $? -eq 0; then
    SYMBOL_XML="<symbol>${SYMBOL_CHAR}</symbol>"
else
    SYMBOL_XML="<!-- <symbol>${SYMBOL_CHAR}</symbol> -->"
fi
AC_SUBST(SYMBOL_XML)

dnl - set ibus-anthy layout
AC_ARG_WITH(layout,
           [AC_HELP_STRING([--with-layout=LAYOUT],
                           [Define the layout. the default is 'jp'.
                            Probably you could set 'default'.])],
           [LAYOUT="$withval"],
           [LAYOUT="jp"])
if test x"$LAYOUT" = x; then
    LAYOUT_XML="<layout>jp</layout>"
else
    LAYOUT_XML="<layout>${LAYOUT}</layout>"
fi
AC_SUBST(LAYOUT_XML)

dnl libtool versioning
dnl
dnl If LT_VERSION_INFO="lt_current:lt_revision:lt_age", libibus is
dnl libibus-ibus_api_version.so.(lt_current - lt_age).lt_age.lt_revision
dnl If the abi is changed, but it is compatible with last version,
dnl ibus_abi_current++, ibus_abi_age++;
dnl If the abi is not compatible with last version,
dnl ibus_abi_current++, ibus_abi_age = 0;
m4_define([lt_current], [ibus_abi_current])
m4_define([lt_revision], [ibus_abi_revision])
m4_define([lt_age], [ibus_abi_age])
LT_VERSION_INFO="lt_current:lt_revision:lt_age"
AC_SUBST(LT_VERSION_INFO)

dnl - define GETTEXT_* variables
GETTEXT_PACKAGE=ibus-anthy
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE,"$GETTEXT_PACKAGE", [Define to the read-only architecture-independent data directory.])

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION(0.16.1)


dnl - OUTPUT files
AC_CONFIG_FILES([ po/Makefile.in
Makefile
ibus-anthy.spec
data/Makefile
gir/Makefile
engine/Makefile
engine/ibus-engine-anthy
engine/anthy.xml.in
setup/Makefile
setup/ibus-setup-anthy
icons/Makefile
m4/Makefile
])

AC_OUTPUT
echo "
                IBus-Anthy version ibus_version

GOBJECT2_CFLAGS          $GOBJECT2_CFLAGS
GOBJECT2_LIBS            $GOBJECT2_LIBS
ANTHY_GOBJECT_LIBDIR     $ANTHY_GOBJECT_LIBDIR
ANTHY_GOBJECT_GIRDIR     $ANTHY_GOBJECT_GIRDIR
ANTHY_GOBJECT_GIRDIR     $ANTHY_GOBJECT_TYPELIBSDIR
LT_VERSION_INFO          $LT_VERSION_INFO
ENV_IBUS_ENGINE          $ENV_IBUS_ENGINE
HAVE_PYGTK2_ANTHY        $enable_pygtk2_anthy
python                   $PYTHON
python-config            $PYTHON_CONFIG
PYTHON_CFLAGS            $PYTHON_CFLAGS
PYTHON_LIBS              $PYTHON_LIBS
ANTHY_ZIPCODE_FILE       $ANTHY_ZIPCODE_FILE
KASUMI_EXEC_FILE         $KASUMI_EXEC_FILE
KASUMI_ICON_FILE         $KASUMI_ICON_FILE
HOTKEYS_XML              $HOTKEYS_XML
SYMBOL_XML               $SYMBOL_XML
LAYOUT_XML               $LAYOUT_XML
"
