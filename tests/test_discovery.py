import pytest

import pysigil.discovery as discovery
from pathlib import PurePosixPath


@pytest.mark.parametrize(
    'name,expected',
    [
        ('My_Plugin', 'my-plugin'),
        ('  fancy.PROVIDER  ', 'fancy-provider'),
        ('Mixed-._Case', 'mixed-case'),
    ],
)
def test_pep503_name(name, expected):
    assert discovery.pep503_name(name) == expected


def test_iter_installed_providers_dedup(monkeypatch):
    class DummyDist:
        def __init__(self, name, files, meta_name=None):
            self.name = name
            self._files = [PurePosixPath(p) for p in files]
            if meta_name is None:
                self.metadata = {}
            else:
                self.metadata = {"Name": meta_name}

        @property
        def files(self):
            return self._files

    dists = [
        DummyDist('pkg_a', ['.sigil/metadata.ini'], 'Foo'),
        DummyDist('pkg_b', ['.sigil/metadata.ini'], 'Foo'),  # duplicate provider id
        DummyDist('pkg_c', ['.sigil/metadata.ini'], 'Bar'),
        DummyDist('pkg_d', ['other.txt'], 'Baz'),  # not a provider
    ]

    monkeypatch.setattr(discovery, 'distributions', lambda: dists)

    providers = list(discovery.iter_installed_providers())
    assert [(pid, name) for pid, name, _ in providers] == [
        ('foo', 'Foo'),
        ('bar', 'Bar'),
    ]
