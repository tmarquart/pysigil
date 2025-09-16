from pathlib import Path

import pytest

from pysigil.authoring import DefaultsValidationError, validate_defaults_file


def _write_ini(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "settings.ini"
    path.write_text(body, encoding="utf-8")
    return path


def test_validate_defaults_allows_underscores(tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, "[demo]\ndefault_loc = ./here\n")
    validate_defaults_file(ini, "demo")


def test_validate_defaults_rejects_leading_underscore(tmp_path: Path) -> None:
    ini = _write_ini(tmp_path, "[demo]\n_invalid = nope\n")
    with pytest.raises(DefaultsValidationError):
        validate_defaults_file(ini, "demo")
