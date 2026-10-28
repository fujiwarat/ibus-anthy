project('ibus-anthy',
  [ 'c' ],
  version: '1.5.19@0@'.format(run_command(
      'sh', '-c',
      '. "@0@" 2>/dev/null; test "x$IBUS_RELEASED" = "x1" && echo -n "" || echo -n "@1@"'.format(
          meson.current_source_dir() / 'meson.config',
          '-beta1'),
      check: true).stdout().strip()),
  default_options: [
    'debug=true',
    'optimization=2',
    'warning_level=1',
  ],
  meson_version: '>= 1.5',
  license: 'GPL-2.0-or-later'
)

# Modules
#-------------------------------------------------

fs = import('fs')
gnome = import('gnome')
i18n = import('i18n')
pkgconfig = import('pkgconfig')
python = import('python').find_installation('python3')
sed = find_program('sed')

# Versioning
#-------------------------------------------------
package_name = meson.project_name()
package_version = meson.project_version()
_version_split = package_version.split('.')
ibus_anthy_major_version = _version_split[0].to_int()
ibus_anthy_minor_version = _version_split[1].to_int()
ibus_anthy_micro_version = _version_split[2].split('-')[0].to_int()

ibus_api_version = '@0@.0'.format(ibus_anthy_major_version)

ibus_abi_current = 5
ibus_abi_age = 0
ibus_abi_revision = (100 * ibus_anthy_minor_version) + ibus_anthy_micro_version
ibus_abi_version = '@0@.@1@.@2@'.format(ibus_abi_current,
                                        ibus_abi_age,
                                        ibus_abi_revision)

# Some variables
#-------------------------------------------------
cc = meson.get_compiler('c')
source_root = meson.current_source_dir()
build_root = meson.current_build_dir()
po_dir = source_root / 'po'
package_string = package_name + '-' + ibus_api_version
pkgdatadir = get_option('prefix') / get_option('datadir') / package_name
ibus_log_domain = 'IBUS_ANTHY'
gettext_package = package_name

# Dependencies
#-------------------------------------------------
min_ibus_version = '1.5.0'
ibus_dep = dependency('ibus-1.0', version: '>=' + min_ibus_version)
min_glib_version = '2.26.0'
gobject_dep = dependency('gobject-2.0', version: '>=' + min_glib_version)

# Check to reconfigure build flags.
# Could be failed due to no RPM_ARCH variable as meson-log.txt explaned.
assert(cc.links('''
int main (int argc, char *argv[]) {
  return 0;
}''',
                name: 'test CFLAGS and LDFLAGS'),
       'Failed to compile and link code with current CFLAGS and LDFLAGS')


# I18N
intl_dep = dependency('intl', required: false)
enable_nls = intl_dep.found()
enable_gnu_gettext = enable_nls

# check anthy
anthy_dep = dependency('anthy-unicode', required: false)
if not anthy_dep.found()
  anthy_dep = dependency('anthy')
endif
anthy_pc = anthy_dep.name()

cc.has_header_symbol('anthy/anthy.h', 'NTH_UNCONVERTED_CANDIDATE',
                     dependencies: anthy_dep, required: true)
cc.has_header_symbol('anthy/anthy.h', 'NTH_KATAKANA_CANDIDATE',
                     dependencies: anthy_dep, required: true)
cc.has_header_symbol('anthy/anthy.h', 'NTH_HIRAGANA_CANDIDATE',
                     dependencies: anthy_dep, required: true)
cc.has_header_symbol('anthy/anthy.h', 'NTH_HALFKANA_CANDIDATE',
                     dependencies: anthy_dep, required: true)

# check the supported IBus version
IBUS_VERSION_TEST='''
from gi import require_version as gi_require_version
gi_require_version("IBus", "1.0")
from gi.repository import IBus
import sys
def _ibus_check_version(v):
    major = IBus.MAJOR_VERSION
    minor = IBus.MINOR_VERSION
    micro = IBus.MICRO_VERSION
    if (major, minor, micro) < tuple(map(int, (v.split(".")))):
        raise ValueError("Required ibus %s but version of ibus is %d.%d.%d" % \
                         (v, major, minor, micro))

_ibus_check_version("@0@")
sys.exit(0)
'''.format(min_ibus_version)
run_command(python, '-c', IBUS_VERSION_TEST, check: true)

# check libanthygobject.so directory
anthy_gobject_libdir = get_option('anthygobject-libdir')
if anthy_gobject_libdir == ''
  anthy_gobject_libdir = \
      anthy_dep.get_variable(pkgconfig: 'prefix') / get_option('libdir')
endif

engine_env = get_option('engine-env')

# check file path of Anthy zipcode.t
anthy_zipcode_file = get_option('anthy-zipcode')
if anthy_zipcode_file == ''
  anthy_zipcode_file = anthy_dep.get_variable(pkgconfig: 'prefix') / \
      get_option('datadir') / anthy_pc / 'zipcode.t'
endif

# check file path of kasumi bin
kasumi_exec = get_option('kasumi-exec')
if kasumi_exec == ''
  kasumi_exec = get_option('prefix') / get_option('bindir') / 'kasumi'
endif

# check file path of kasumi icon
kasumi_icon = get_option('kasumi-icon')
if kasumi_icon == ''
  kasumi_icon = \
      get_option('prefix') / get_option('datadir') / 'pixmaps' / 'kasumi.png'
endif

assert(get_option('on-off-keys').length() > 0)
on_off_key = '\'@0@\''.format('\', \''.join(get_option('on-off-keys')))

icon_preference = 'preferences-desktop'

hotkeys_xml = '<!-- <hotkeys></hotkeys> -->'

# check symbol in IBus.EngineDesc
symbol_char = '&#x3042;'
symbol_char_int = 0x3042
ENGINE_SYMBOL_TEST = '''
import sys
from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')
from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_symbol'))
'''
if run_command(python, '-c', ENGINE_SYMBOL_TEST, check: false).returncode() == 0
  symbol_xml = '<symbol>@0@</symbol>'.format(symbol_char)
else
  error('ibus 1.4 or later supports symbol in IBus.EngineDesc')
endif

# check symbol in IBus.Property
PROPERTY_SYMBOL_TEST='''
import sys
from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')
from gi.repository import IBus
exit(not hasattr(IBus.Property, 'get_symbol'))
'''
if run_command(python, '-c', PROPERTY_SYMBOL_TEST,
               check: false).returncode() != 0
  error('ibus 1.5 or later supports symbol in IBus.Property')
endif

# check XKB option in IBus.EngineDesc
LAYOUT_OPTION_TEST='''
import sys
from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')
from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_layout_option'))
'''
if run_command(python, '-c', LAYOUT_OPTION_TEST, check: false).returncode() != 0
  error('ibus 1.5 or later supports layout_option in IBus.EngineDesc')
endif

# check get_version in IBus.EngineDesc
DESC_VERSION_TEST='''
import sys
from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')
from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_version'))
'''
if run_command(python, '-c', DESC_VERSION_TEST, check: false).returncode() != 0
  error('ibus 1.5 or later supports version in IBus.EngineDesc')
endif

# check icon_prop_key in IBus.EngineDesc
ICON_PROP_KEY_TEST='''
import sys
from gi import require_version as gi_require_version
gi_require_version('IBus', '1.0')
from gi.repository import IBus
exit(not hasattr(IBus.EngineDesc, 'get_icon_prop_key'))
'''
if run_command(python, '-c', ICON_PROP_KEY_TEST,
               check: false).returncode() == 0
  icon_prop_key_xml = '<icon_prop_key>InputMode</icon_prop_key>'
else
  icon_prop_key_xml = '<!-- <icon_prop_key>InputMode</icon_prop_key> -->'
  warning('ibus 1.5.11 or later supports icon-prop-key in IBus.EngineDesc')
endif

# set ibus-anthy layout
default_layout = get_option('keyboard-layout')
if default_layout == ''
  default_layout = 'jp'
endif
layout_xml='<layout>@0@</layout>'.format(default_layout)

# Bindings
introspection_dep = dependency('gobject-introspection-1.0', version: '>= 0.6.8',
                               required: true)
introspection_args = [ '--warn-all', ]
if introspection_dep.version().version_compare('>=1.83.2')
  introspection_args += [ '--doc-format=gi-docgen', ]
endif

# Default CFLAGS and LDFLAGS
config_h_inc = include_directories('.')

_ibus_cflags = [ '-DHAVE_CONFIG_H' ]

cc_default_multi_warn_arguments = [
  [ '-Werror=format-security' ]
]

env_CFLAGS = run_command(python, '-c',
                         'import os; print(os.getenv("CFLAGS", ""))',
                         check: true).stdout().strip()
env_CFLAGS_has_fortify = false

foreach e : env_CFLAGS.split() + get_option('c_args')
  if e.contains('-D_FORTIFY_SOURCE=')
    env_CFLAGS_has_fortify = true
    break
  endif
endforeach

# Set default single arguments
ibus_cflags =  cc.get_supported_arguments(_ibus_cflags)

# Need '-Wall -O2 -D_FORTIFY_SOURCE=2' to enable '-Wunused-result'
if not env_CFLAGS_has_fortify and get_option('optimization') != '0'
  foreach i : [ 3, 2 ]
    _ibus_cflags2 = '-D_FORTIFY_SOURCE=@0@'.format(i)
    if cc.has_argument(_ibus_cflags2)
      ibus_cflags += _ibus_cflags2
      break
    endif
  endforeach
endif

# cc.get_supported_arguments() does not support long nested arguments
if env_CFLAGS == '' and get_option('warning_level') != '0'
  foreach args : cc_default_multi_warn_arguments
    test_args = [ '-Wall' ] + args
    if cc.has_multi_arguments(test_args)
      ibus_cflags +=  args
    endif
  endforeach
endif

add_project_arguments(ibus_cflags, language: 'c')

# Subdirectories
#-------------------------------------------------
subdir('po')
subdir('data')
subdir('gir')
subdir('engine')
subdir('icons')
subdir('setup')
subdir('tests')


# RPM Spec file
#-------------------------------------------------
ibus_rpm_spec = configure_file(
  input: '@0@.spec.in'.format(package_name),
  output: '@BASENAME@',
  configuration: {
    'PACKAGE_NAME': package_name,
    'PACKAGE_VERSION': package_version.replace('-', '~'),
    'DATE_DISPLAY': run_command('date', '+%a %b %d %Y',
                                check: true).stdout().strip(),
  },
)

summary({
  'CFLAGS':                        get_option('c_args') + ibus_cflags,
  'LDFLAGS':                       get_option('c_link_args'),
  'Debug':                         get_option('debug'),
  'Optimization':                  get_option('optimization'),
  'Warning level':                 get_option('warning_level'),
  'Install prefix':                get_option('prefix'),
}, section: 'Build')

summary({
  'PYTHON':                        python,
}, section: 'Python')

summary({
  'GOBJECT2 VERSION':              gobject_dep.version(),
  'ANTHY_PC':                      anthy_pc,
  'ANTHY VERSION':                 anthy_dep.version(),
  'ANTHY_GOBJECT_LIBDIR':          anthy_gobject_libdir,
  'ANTHY_ZIPCODE_FILE':            anthy_zipcode_file,
  'KASUMI_EXEC_FILE':              kasumi_exec,
  'KASUMI_ICON_FILE':              kasumi_icon,
  'ON_OFF_KEYS':                   on_off_key,
  'SYMBOL_XML':                    symbol_xml,
  'ICON_PROP_KEY_XML':             icon_prop_key_xml,
  'LAYOUT_XML':                    layout_xml,
}, section: 'Components')

summary({
  'Install tests':                 get_option('install-tests'),
}, section: 'Tests')

meson.add_dist_script(python.full_path(), source_root / 'meson-dist.py')
