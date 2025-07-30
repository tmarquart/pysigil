import textwrap
from pathlib import Path

import pytest

from sigil.errors import SigilMetaError
from sigil.helpers import load_meta


def test_csv_happy_path(tmp_path: Path):
    csv_text = textwrap.dedent(
        """\
        key,title,tooltip,type,choices,secret,min,max,order,advanced
        ui.theme,Theme,"Line1, line2",choice,light|dark|system,,, ,10,
        db.port,Database Port,,int,,,1024,65535,20,false
        secret.api_key,API Key,Stored securely in OS keychain,str,,true,, ,30,true
        """
    )
    path = tmp_path / "defaults.meta.csv"
    path.write_text(csv_text, encoding="utf-8")

    meta = load_meta(path)
    assert meta["ui.theme"]["choices"] == ["light", "dark", "system"]
    assert meta["db.port"]["min"] == 1024
    assert meta["db.port"]["max"] == 65535
    assert meta["secret.api_key"]["secret"] is True
    assert meta["secret.api_key"]["advanced"] is True
    assert meta["ui.theme"]["tooltip"] == "Line1, line2"


def test_csv_quoted_tooltip(tmp_path: Path):
    csv_text = "key,title,tooltip\n" "a,Alpha,\"Line1,\nline2\"\n"
    path = tmp_path / "meta.csv"
    path.write_text(csv_text, encoding="utf-8")

    meta = load_meta(path)
    assert meta["a"]["tooltip"] == "Line1,\nline2"


def test_csv_duplicate_key(tmp_path: Path):
    csv_text = "key\nfoo\nfoo\n"
    path = tmp_path / "meta.csv"
    path.write_text(csv_text, encoding="utf-8")

    with pytest.raises(SigilMetaError):
        load_meta(path)


def test_csv_min_gt_max(tmp_path: Path):
    csv_text = "key,min,max\nfoo,10,5\n"
    path = tmp_path / "meta.csv"
    path.write_text(csv_text, encoding="utf-8")

    with pytest.raises(SigilMetaError):
        load_meta(path)


def test_csv_invalid_number(tmp_path: Path):
    csv_text = "key,min\nfoo,abc\n"
    path = tmp_path / "meta.csv"
    path.write_text(csv_text, encoding="utf-8")

    with pytest.raises(SigilMetaError):
        load_meta(path)


