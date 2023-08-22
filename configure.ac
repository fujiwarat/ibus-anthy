# vim:set et ts=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2010-2023 Takao Fujiwara <takao.fujiwara1@gmail.com>
# Copyright (c) 2007-2021 Red Hat, Inc.
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

dnl - if not 1, append datestamp to the version number.
m4_define([ibus_anthy_released], [1])
m4_define([ibus_anthy_major_version], [1])
m4_define([ibus_anthy_minor_version], [5])
m4_define([ibus_anthy_micro_version], [15])
m4_define([ibus_abi_current], [5])
m4_define([ibus_abi_revision],
          [m4_eval(100 * ibus_anthy_minor_version + ibus_anthy_micro_version)])
m4_define([ibus_abi_age], [0])
m4_define(ibus_maybe_datestamp,
    m4_esyscmd([if test x]ibus_anthy_released[ != x1; then date +.%Y%m%d | tr -d '\n\r'; fi]))

m4_define([ibus_anthy_version],
    ibus_anthy_major_version.ibus_anthy_minor_version.ibus_anthy_micro_version[]ibus_maybe_datestamp)
m4_define([ibus_required_version], [1.5.0])
m4_define([glib_required_version], [2.26.0])

AC_INIT([ibus-anthy], [ibus_anthy_version], [https://github.com/ibus/ibus-anthy/issues],[ibus-anthy])
AM_INIT_AUTOMAKE([1.10])
AC_GNU_SOURCE

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])

dnl - define PACKAGE_VERSION_* variables
AS_VERSION
AS_NANO
AM_SANITY_CHECK
AM_MAINTAINER_MODE(enable)
AC_DISABLE_STATIC
AC_PROG_CC
AM_PROG_CC_C_O
AC_PROG_CXX
AC_HEADER_STDC
LT_INIT

dnl - For dislpay Date
m4_define(ibus_datedisplay,
    m4_esyscmd(date '+%a %b %d %Y' | tr -d '\n\r'))
DATE_DISPLAY="ibus_datedisplay"
AC_SUBST(DATE_DISPLAY)

dnl - check anthy
PKG_CHECK_MODULES(ANTHY, [anthy-unicode], [ANTHY_PC=anthy-unicode], [
    PKG_CHECK_MODULES(ANTHY, [anthy], [ANTHY_PC=anthy])
])
AC_SUBST(ANTHY_PC)

CFLAGS_backup="$CFLAGS"
CFLAGS="$ANTHY_CFLAGS $CFLAGS"
AC_CHECK_DECLS([
NTH_UNCONVERTED_CANDIDATE,
NTH_KATAKANA_CANDIDATE,
NTH_HIRAGANA_CANDIDATE,
NTH_HALFKANA_CANDIDATE],,
    AC_MSG_ERROR([Could not find NTH_*_CANDIDATE values in anthy.h]),
    [[#include <anthy/anthy.h>]])
CFLAGS="$CFLAGS_backup"

PKG_CHECK_MODULES(GOBJECT2, [
    gobject-2.0 >= glib_required_version
])

dnl - GObject introspection
GOBJECT_INTROSPECTION_REQUIRE([0.6.8])

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

dnl - define python version
AC_ARG_WITH(python,
    AS_HELP_STRING([--with-python[=PATH]],
        [Select python2 or python3]),
    [PYTHON=$with_python], []
)

dnl export $pyexecdir using existent $PYTHON
AM_PATH_PYTHON([2.5])

dnl Decided to separate python3 directory from python2 directory here
dnl because engine/table.py includes unicode array so it's better to
dnl use __future__.unicode_literals.
dnl python3 string are always str.
dnl In case __future__.unicode_literals is imported, all the literal
dnl 'a' is treated as unicode and u'a' is not needed in python2.
dnl But str is not unicode so we need to convert str to unicode in
dnl python2 for all non-literal variables likes return values of
dnl gettext, IBusConfig.get_value, get methods in GTK+ and so on.
dnl It would causes to complicate python2 codes if merge python2 and
dnl python3 in the same file.
dnl if sys.version < '3':
dnl     return unicode(gettext(a), 'utf-8')
dnl else:
dnl     return gettext(a)
case "$PYTHON_VERSION" in
3.*)
    enable_python3=yes
    enable_python2=no
    ;;
*)
    enable_python3=no
    enable_python2=yes
    ;;
esac

AM_CONDITIONAL([ENABLE_PYTHON2], [test x"$enable_python2" = x"yes"])
AM_CONDITIONAL([ENABLE_PYTHON3], [test x"$enable_python3" = x"yes"])

dnl - check the supported ibus version
AC_MSG_CHECKING([if your ibus version is supported])
IBUS_VERSION_TEST="
from gi.repository import IBus
def _ibus_check_version(v):
    major = IBus.MAJOR_VERSION
    minor = IBus.MINOR_VERSION
    micro = IBus.MICRO_VERSION
    if (major, minor, micro) < tuple(map(int, (v.split('.')))):
        raise ValueError('Required ibus %s but version of ibus is %d.%d.%d' % \
                         (v, major, minor, micro))

_ibus_check_version('ibus_required_version')
exit(0)
"
$PYTHON -c "$IBUS_VERSION_TEST"
if test $? -eq 0; then
AC_MSG_RESULT([yes])
else
AC_MSG_ERROR([no])
fi

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
              [],
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
           [ANTHY_ZIPCODE_FILE="$datadir/$ANTHY_PC/zipcode.t"])
test "x$prefix" = xNONE && prefix=$ac_default_prefix
eval ANTHY_ZIPCODE_FILE=$ANTHY_ZIPCODE_FILE
eval ANTHY_ZIPCODE_FILE=$ANTHY_ZIPCODE_FILE
AC_SUBST(ANTHY_ZIPCODE_FILE)
AM_CONDITIONAL([ENABLE_ZIPCODE], [test -f "$ANTHY_ZIPCODE_FILE" ])

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

dnl - check preference icon name
# Replaced the legacy icon gtk-preferences with preferences-desktop
# because the icon is included in gnome-icon-theme-legacy package.
# The following fix would be needed for old non-GNOME desktops.
# https://github.com/ibus/ibus/commit/dd6acfa5013b
# Otherwise you can specify the preference icon for your desktop.
AC_ARG_WITH(icon-preference,
           [AC_HELP_STRING([--with-icon-preference=ICON_NAME],
                           [preference icon name.])],
           [ICON_PREFERENCE="$withval"],
           [ICON_PREFERENCE='preferences-desktop'])
AC_SUBST(ICON_PREFERENCE)

dnl - check private png
AC_MSG_CHECKING([if you install the private png file])
AC_ARG_ENABLE(private-png,
              AS_HELP_STRING([--enable-private-png=no/yes],
                             [Install ibus-anthy.png default=no]),
              [],
              enable_private_png=no)
AC_MSG_RESULT($enable_private_png)

if test x"$enable_private_png" = xyes; then
    AM_CONDITIONAL(HAVE_PRIVATE_PNG, true)
else
    AM_CONDITIONAL(HAVE_PRIVATE_PNG, false)
fi

dnl - check on-off keys
AC_ARG_WITH(on-off-keys,
           [AC_HELP_STRING([--with-on-off-keys="'KEY1','KEY2',..."],
                           [Anthy default on-off keys. default="
                            'Zenkaku_Hankaku', 'Ctrl+J'".])],
           [ON_OFF_KEYS="$withval"],
           [ON_OFF_KEYS="'Zenkaku_Hankaku', 'Ctrl+J'"])
AC_SUBST(ON_OFF_KEYS)

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

dnl - check symbol in IBus.EngineDesc
AC_MSG_CHECKING([if IBus.EngineDesc has get_symbol])
SYMBOL_CHAR='&#x3042;'
SYMBOL_CHAR_INT=0x3042
SYMBOL_TEST="from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_symbol'))
"
$PYTHON -c "$SYMBOL_TEST"
if test $? -eq 0; then
    SYMBOL_XML="<symbol>${SYMBOL_CHAR}</symbol>"
    AC_MSG_RESULT([yes])
else
    SYMBOL_XML="<!-- <symbol>${SYMBOL_CHAR}</symbol> -->"
    AC_MSG_ERROR([ibus 1.4 or later supports symbol in IBus.EngineDesc])
fi
AC_SUBST(SYMBOL_CHAR_INT)
AC_SUBST(SYMBOL_XML)

dnl - check symbol in IBus.Property
AC_MSG_CHECKING([if IBus.Property has get_symbol])
SYMBOL_TEST="from gi.repository import IBus
exit(not hasattr(IBus.Property, 'get_symbol'))
"
$PYTHON -c "$SYMBOL_TEST"
if test $? -eq 0; then
    AC_MSG_RESULT([yes])
else
    AC_MSG_ERROR([ibus 1.5 or later supports symbol in IBus.Property])
fi

dnl - check XKB option in IBus.EngineDesc
AC_MSG_CHECKING([if IBus.EngineDesc has get_layout_option])
LAYOUT_OPTION_TEST="from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_layout_option'))
"
$PYTHON -c "$LAYOUT_OPTION_TEST"
if test $? -eq 0; then
    AC_MSG_RESULT([yes])
else
    AC_MSG_ERROR([ibus 1.5 or later supports layout_option in IBus.EngineDesc])
fi

AC_MSG_CHECKING([if IBus.EngineDesc has get_version])
DESC_VERSION_TEST="from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_version'))
"
$PYTHON -c "$DESC_VERSION_TEST"
if test $? -eq 0; then
    AC_MSG_RESULT([yes])
else
    AC_MSG_ERROR([ibus 1.5 or later supports version in IBus.EngineDesc])
fi

dnl - check icon_prop_key in IBus.EngineDesc
AC_MSG_CHECKING([if IBus.EngineDesc has get_icon_prop_key])
ICON_PROP_KEY_TEST="from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_icon_prop_key'))
"
$PYTHON -c "$ICON_PROP_KEY_TEST"
if test $? -eq 0; then
    ICON_PROP_KEY_XML="<icon_prop_key>InputMode</icon_prop_key>"
    AC_MSG_RESULT([yes])
else
    ICON_PROP_KEY_XML="<!-- <icon_prop_key>InputMode</icon_prop_key> -->"
    AC_MSG_RESULT([ibus 1.5.11 or later supports icon-prop-key in IBus.EngineDesc])
fi
AC_SUBST(ICON_PROP_KEY_XML)

dnl - set ibus-anthy layout
AC_ARG_WITH(layout,
           [AC_HELP_STRING([--with-layout=LAYOUT],
                           [Define the layout. the default is 'jp'.
                            Probably you could set 'default'.])],
           [LAYOUT="$withval"],
           [LAYOUT="jp"])
if test x"$LAYOUT" = x; then
    LAYOUT="jp"
fi
LAYOUT_XML="<layout>${LAYOUT}</layout>"
AC_SUBST(LAYOUT)
AC_SUBST(LAYOUT_XML)

dnl --enable-installed-tests
AC_ARG_ENABLE(installed-tests,
    AS_HELP_STRING([--enable-installed-tests],
                   [Enable to installed tests]),
    [enable_installed_tests=$enableval],
    [enable_installed_tests=no]
)
AM_CONDITIONAL([ENABLE_INSTALLED_TESTS],
               [test x"$enable_installed_tests" = x"yes"])
if test x"$enable_installed_tests" = x"no"; then
    enable_installed_tests="no (disabled, use --enable-installed-tests to enable)"
fi


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

AC_DEFINE_UNQUOTED(
  GETTEXT_PACKAGE, "$GETTEXT_PACKAGE",
    [Define to the read-only architecture-independent data directory.]
)

AM_GNU_GETTEXT_VERSION([0.19.8])
AM_GNU_GETTEXT([external])


dnl - OUTPUT files
AC_CONFIG_FILES([
po/Makefile.in
Makefile
ibus-anthy.spec
data/Makefile
gir/Makefile
engine/Makefile
engine/python2/Makefile
engine/python2/anthy.inputMethod.xml.in
engine/python2/default.inputMethod.xml.in
engine/python3/Makefile
engine/python3/anthy.inputMethod.xml.in
engine/python3/default.inputMethod.xml.in
setup/Makefile
setup/python2/Makefile
setup/python3/Makefile
tests/Makefile
icons/Makefile
m4/Makefile
])

AC_OUTPUT
echo "
                IBus-Anthy version ibus_anthy_version

GOBJECT2_CFLAGS             $GOBJECT2_CFLAGS
GOBJECT2_LIBS               $GOBJECT2_LIBS
ANTHY_PC                    $ANTHY_PC
ANTHY_CFLAGS                $ANTHY_CFLAGS
ANTHY_LIBS                  $ANTHY_LIBS
ANTHY_GOBJECT_LIBDIR        $ANTHY_GOBJECT_LIBDIR
ANTHY_GOBJECT_GIRDIR        $ANTHY_GOBJECT_GIRDIR
ANTHY_GOBJECT_TYPELIBSDIR   $ANTHY_GOBJECT_TYPELIBSDIR
LT_VERSION_INFO             $LT_VERSION_INFO
ENV_IBUS_ENGINE             $ENV_IBUS_ENGINE
HAVE_PYGTK2_ANTHY           $enable_pygtk2_anthy
python                      $PYTHON
Enable python2              $enable_python2
Enable python3              $enable_python3
python-config               $PYTHON_CONFIG
PYTHON_CFLAGS               $PYTHON_CFLAGS
PYTHON_LIBS                 $PYTHON_LIBS
ANTHY_ZIPCODE_FILE          $ANTHY_ZIPCODE_FILE
KASUMI_EXEC_FILE            $KASUMI_EXEC_FILE
KASUMI_ICON_FILE            $KASUMI_ICON_FILE
ICON_PREFERENCE             $ICON_PREFERENCE
ON_OFF_KEYS                 $ON_OFF_KEYS
HOTKEYS_XML                 $HOTKEYS_XML
SYMBOL_XML                  $SYMBOL_XML
ICON_PROP_KEY_XML           $ICON_PROP_KEY_XML
LAYOUT_XML                  $LAYOUT_XML
"
