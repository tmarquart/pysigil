from pysigil.api import FieldInfo
from pysigil.ui.sections import bucket_by_section, compute_section_order, field_sort_key


def _f(key: str, *, section: str | None = None, order: int | None = None, label: str | None = None):
    return FieldInfo(
        key=key,
        type="string",
        label=label,
        description_short=None,
        description=None,
        section=section,
        order=order,
    )


def test_bucket_and_ordering():
    fields = [
        _f("a", section="Network"),
        _f("b", section=None),
        _f("c", section="network", order=1),
        _f("d", section="Untracked"),
    ]
    sec_order = compute_section_order(fields, ["Paths"])
    assert sec_order == ["Paths", "Network", "Other", "Untracked"]

    groups = bucket_by_section(fields)
    assert set(groups.keys()) == {"Network", "Other", "Untracked"}
    assert [f.key for f in sorted(groups["Network"], key=field_sort_key)] == ["c", "a"]


def test_field_sort_key_labels():
    fields = [
        _f("a", section="Misc", order=None, label="zeta"),
        _f("b", section="Misc", order=None, label="beta"),
    ]
    sorted_keys = [f.key for f in sorted(fields, key=field_sort_key)]
    assert sorted_keys == ["b", "a"]
