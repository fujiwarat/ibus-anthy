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
               'engine.py', 'factory.py', 'jastring.py', 'kana.py', 'main.py',
               'romaji.py', 'segment.py', 'tables.py', 'thumb.py',
             ],
             install_dir: pkgdatadir / 'engine',
)


foreach name : [ 'anthy', 'default', ]
  install_dir = ''
  if name == 'anthy'
    install_dir = \
        get_option('prefix') / get_option('datadir') / 'ibus' / 'component'
  elif name == 'default'
    install_dir = pkgdatadir / 'engine'
  else
    error('No install_dir for @0@'.format(name))
  endif

  configure_file(
    input: '@0@.inputMethod.xml.in.in'.format(name),
    output: '@0@.xml'.format(name),
    configuration: {
      'HOTKEYS_XML': hotkeys_xml,
      'ICON_PROP_KEY_XML': icon_prop_key_xml,
      'LAYOUT_XML': layout_xml,
      'LIBEXECDIR': get_option('prefix') / get_option('libexecdir'),
      'PACKAGE_VERSION': package_version,
      'PKGDATADIR': pkgdatadir,
      'SYMBOL_XML': symbol_xml,
    },
    install: true,
    install_dir: install_dir,
  )
endforeach


env_ibus_engine = ''
if engine_env != ''
  env_ibus_engine = '@0@ @1@'.format(find_program('env').full_path(),
                                     engine_env)
endif


configure_file(
  input: 'ibus-engine-anthy.in',
  output: '@BASENAME@',
  configuration: {
    'prefix': get_option('prefix'),
    'exec_prefix': get_option('prefix'),
    'libexecdir': get_option('prefix') / get_option('libexecdir'),
    'datarootdir': get_option('prefix') / get_option('datadir'),
    'PACKAGE': package_name,
    'PYTHON': python.full_path(),
    'ENV_IBUS_ENGINE': env_ibus_engine,
  },
  install: true,
  install_dir: get_option('libexecdir'),
  install_mode: 'rwxr-xr-x',
)
