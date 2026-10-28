test_execsdir = \
  get_option('prefix') / get_option('libexecdir') / 'installed-tests' / 'ibus-anthy'
test_sourcesdir = \
  get_option('prefix') / get_option('datadir') / 'installed-tests' / 'ibus-anthy'

test('test', files('test-build.sh'),
    args: [ '--builddir', meson.current_build_dir(),
            '--srcdir', meson.current_source_dir(),
          ],
)

test_env = ''
if pkgdatadir / 'engine' != '/usr/share/ibus/anthy/engine'
  test_env = '@0@ IBUS_ANTHY_ENGINE_PATH=@1@'.format (engine_env,
                                                      pkgdatadir / 'engine')
endif
if test_env != ''
  test_env = '@0@ @1@ '.format(find_program('env').full_path(), test_env)
endif

if get_option('install-tests')
  foreach name : [ 'anthytest' ]
    configure_file(
      input: 'meta.test.in',
      output: '@0@.test'.format(name),
      configuration: {
        'TEST_EXEC': test_execsdir / '@0@.py'.format(name),
        'TEST_SRCDIR': test_sourcesdir,
        'TEST_ENV': test_env,
      },
      install_dir: test_sourcesdir,
    )
  endforeach

  install_data(
    [ 'anthycases.py', 'anthytest.py' ],
    install_dir: test_execsdir,
    install_mode: 'rwxr-xr-x',
  )
endif
