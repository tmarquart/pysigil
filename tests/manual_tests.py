from pysigil.settings_metadata import ProviderSpec,FieldSpec

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