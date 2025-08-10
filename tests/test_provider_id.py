
from pysigil.provider_id import pep503_name


def test_pep503_normalisation_examples():
    cases = {
        "Accio_Data": "accio-data",
        "my.package": "my-package",
        "cool-pkg": "cool-pkg",
    }
    for inp, expected in cases.items():
        assert pep503_name(inp) == expected


def test_pep503_collisions():
    names = ["a.b", "a-b", "a_b"]
    normalised = {pep503_name(n) for n in names}
    assert normalised == {"a-b"}
