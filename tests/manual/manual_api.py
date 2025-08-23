from pysigil.api import *
from pysigil.settings_metadata import add_field_spec

print(providers())

#register_provider('sigil_dummy',title='sigil dummy',description='a NEW dummy for sigil')
print(get_provider('sigil_dummy'))
#register_provider('new_provider',title='sigil dummy',description='a dummy for sigil')
#print(get_provider('new_provider'))

prov=handle('sigil_dummy')
#prov.add_field('api_field','string')