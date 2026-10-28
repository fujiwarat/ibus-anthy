anthy_symbolmap = meson.current_source_dir() / 'libanthygobject.map'
ibus_linkflags = cc.get_supported_link_arguments(
  '-Wl,--version-script,@0@'.format(anthy_symbolmap),
)

libanthygobject = library('anthygobject-@0@'.format(ibus_api_version),
  [
    files('anthygcontext.c'),
  ],
  dependencies: [ gobject_dep, anthy_dep ],
  link_args: ibus_linkflags,
  include_directories: config_h_inc,
  version: ibus_abi_version,
  install: true,
  install_dir: anthy_gobject_libdir,
)

anthygobject_headers = [ 'anthygcontext.h' ]

install_headers(anthygobject_headers,
  install_dir: '@0@'.format(
      get_option('prefix') / get_option('includedir') / 'ibus-anthy-@0@'.format(
          ibus_api_version)
  ),
)

libanthygobject_dep = declare_dependency(
  link_with: libanthygobject,
  include_directories: config_h_inc,
  sources: files(anthygobject_headers),
)

anthy_includedir = run_command('pkg-config', '--variable=includedir',
                               anthy_pc,
                               check: true).stdout().strip()

ibus_gir_args = introspection_args
if not introspection_dep.version().version_compare('>=0.9.6')
  ibus_gir_args += [ '--strip-prefix=IBus', ]
endif

anthy_gir = gnome.generate_gir(libanthygobject,
  sources: anthygobject_headers + anthy_includedir / 'anthy' / 'anthy.h',
  namespace: 'Anthy',
  nsversion: ibus_api_version,
  identifier_prefix: 'Anthy',
  symbol_prefix: [ 'anthy' ],
  header: anthygobject_headers,
  includes: [ 'GObject-2.0' ],
  extra_args: ibus_gir_args,
  install: true,
)
