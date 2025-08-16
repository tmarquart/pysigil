from pathlib import Path
import pytest

from pysigil.root import ProjectRootNotFoundError, find_project_root


def test_project_root_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ProjectRootNotFoundError):
        find_project_root(start=tmp_path)
