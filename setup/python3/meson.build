config_py = configure_file(
  input: '_config.py.in',
  output: '@BASENAME@',
  configuration: {
    'pkgdatadir': pkgdatadir,
    'libexecdir': get_option('prefix') / get_option('libexecdir'),
    'datadir': get_option('prefix') / get_option('datadir'),
    'ANTHY_PC': anthy_pc,
    'LAYOUT': default_layout,
    'SYMBOL_CHAR_INT': symbol_char_int,
    'ICON_PREFERENCE': icon_preference,
    'VERSION': package_version,
  },
)

install_data([
               config_py,
               'anthyprefs.py', 'main.py', 'prefs.py', 'setup.ui',
             ],
             install_dir: pkgdatadir / 'setup',
)

configure_file(
  input: 'ibus-setup-anthy.in',
  output: '@BASENAME@',
  configuration: {
    'datadir': get_option('prefix') / get_option('datadir'),
    'localedir': get_option('prefix') / get_option('localedir'),
    'PACKAGE': package_name,
    'PYTHON': python.full_path(),
  },
  install: true,
  install_dir: get_option('libexecdir'),
  install_mode: 'rwxr-xr-x',
)

desktop_in_file = configure_file(
  input: 'ibus-setup-anthy.desktop.in.in',
  output: '@BASENAME@',
  configuration: {
    'libexecdir': get_option('prefix') / get_option('libexecdir'),
    'pkgdatadir': get_option('prefix') / get_option('datadir'),
  },
)

i18n.merge_file(
  input: desktop_in_file,
  output: '@BASENAME@',
  type: 'desktop',
  po_dir: po_dir,
  install: true,
  install_dir: get_option('datadir') / 'applications'
)

gnome.post_install(update_desktop_database: true)
