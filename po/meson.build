# These options get passed to xgettext.
# The last argument --keyword without keyword prevents xgettext from
# extracting translatable strings from "Icon" in *.desktop files.
ibus_preset_args = [
  '--from-code=UTF-8',
  '--keyword=_',
  '--keyword=N_',
  '--keyword=C_:1c,2',
  '--keyword=NC_:1c,2',
  '--keyword=g_dngettext:2,3',
  '--add-comments',
  '--keyword=Name',
  '--keyword=Comment',
  '--keyword',
]

i18n.gettext(gettext_package,
  args: ibus_preset_args,
)
