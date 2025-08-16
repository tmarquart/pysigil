import pysigil.discovery as discovery
import pytest


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


def test_iter_providers_dedup_and_groups(monkeypatch):
    class DummyDist:
        def __init__(self, name, meta_name=None):
            self.name = name
            if meta_name is None:
                self.metadata = {}
            else:
                self.metadata = {'Name': meta_name}

    class DummyEP:
        def __init__(self, dist, group):
            self.dist = dist
            self.group = group

    eps = [
        DummyEP(DummyDist('pkg_a', 'Foo'), 'pysigil_providers'),
        DummyEP(DummyDist('pkg_b', 'Foo'), 'pysigil.providers'),  # duplicate provider id
        DummyEP(DummyDist('pkg_c', 'Bar'), 'pysigil.providers'),
    ]

    class DummyEPs:
        def select(self, *, group):
            return [ep for ep in eps if ep.group == group]

    monkeypatch.setattr(discovery, 'entry_points', lambda: DummyEPs())

    providers = list(discovery.iter_providers())
    assert [(pid, name) for pid, name, _ in providers] == [
        ('foo', 'Foo'),
        ('bar', 'Bar'),
    ]
