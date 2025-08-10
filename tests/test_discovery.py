from types import SimpleNamespace

from pysigil import discovery


def test_iter_providers_dedup(monkeypatch):
    dist1 = SimpleNamespace(metadata={"Name": "My_pkg"})
    dist2 = SimpleNamespace(metadata={"Name": "my-pkg"})
    dist3 = SimpleNamespace(metadata={"Name": "Other"})
    ep1 = SimpleNamespace(dist=dist1)
    ep2 = SimpleNamespace(dist=dist2)
    ep3 = SimpleNamespace(dist=dist3)

    class FakeEntryPoints:
        def select(self, *, group):
            mapping = {
                "pysigil_providers": [ep1, ep2],
                "pysigil.providers": [ep3],
            }
            return mapping.get(group, [])

    monkeypatch.setattr(discovery, "entry_points", lambda: FakeEntryPoints())
    providers = list(discovery.iter_providers())
    assert providers == [
        ("my-pkg", "My_pkg", dist1),
        ("other", "Other", dist3),
    ]
