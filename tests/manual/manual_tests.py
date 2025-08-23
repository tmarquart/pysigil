from pysigil.settings_metadata import ProviderSpec,FieldSpec,save_provider_spec,load_provider_spec,register_provider,add_field_spec
from pysigil.paths import user_config_dir
import os

spec = ProviderSpec(
    provider_id="my-pkg",
    schema_version="0.1",
    title="My Package Settings",
    fields=[
        FieldSpec(key="retries", type="integer", label="Retries"),
        FieldSpec(key="verbose", type="boolean", label="Verbose"),
    ],
)

print(spec.fields)

register_provider(user_config_dir("my-pkg"),'my-pkg','0.1')
#add_field_spec(os.path.join(user_config_dir('my-pkg'))
