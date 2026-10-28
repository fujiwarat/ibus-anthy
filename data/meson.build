install_data('oldchar.t', 'symbol.t', install_dir: pkgdatadir / 'dicts')

# rf. i18n metainfo.xml
# http://www.freedesktop.org/software/appstream/docs/sect-Quickstart-Translation.html
i18n.merge_file(
  input: 'ibus-anthy.appdata.xml.in',
  output: 'org.freedesktop.ibus.engine.anthy.metainfo.xml',
  type: 'xml',
  po_dir: po_dir,
  install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

configure_file(
  input: 'org.freedesktop.ibus.engine.anthy.gschema.xml.in',
  output: '@BASENAME@',
  configuration: {
    'ANTHY_ZIPCODE_FILE': anthy_zipcode_file,
    'KASUMI_EXEC_FILE': kasumi_exec,
    'KASUMI_EXEC_BASENAME': fs.name(kasumi_exec),
    'KASUMI_ICON_FILE': kasumi_icon,
    'ON_OFF_KEYS': on_off_key,
    'PYTHON': python.full_path(),
    'pkgdatadir': pkgdatadir,
  },
  install: true,
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

custom_target('emoji.t',
  input: [ 'emoji-each.t', 'emoji-emoji.t' ],
  output: 'emoji.t',
  command: [ python, files('emoji-gen.py'),
             '@INPUT0@', '@INPUT1@', '@OUTPUT@' ],
  build_by_default: true,
  install: true,
  install_dir: pkgdatadir / 'dicts',
)

if fs.exists(anthy_zipcode_file)
  custom_target('zipcode.t',
    input: anthy_zipcode_file,
    output: 'zipcode.t',
    command: [ python, files('zipcode-textdic.py'), '@INPUT@',
               meson.current_build_dir(),
             ],
    build_by_default: fs.exists(anthy_zipcode_file),
    install: true,
    install_dir: pkgdatadir / 'dicts',
  )
endif

if run_command(python, files('era.py'), '--check', files('era.t'),
               check: false).returncode() != 0
  custom_target('era.t',
    input: 'era.t.in',
    output: 'era.t',
    command: [ python, files('era.py'), '@INPUT@', '--output', '@OUTPUT@' ],
    build_by_default: true,
    install: true,
    install_dir: pkgdatadir / 'dicts',
  )
else
  install_data('era.t', install_dir: pkgdatadir / 'dicts')
endif

gnome.post_install(glib_compile_schemas: true)
