from __future__ import annotations

from pathlib import Path

from pysigil.root import ProjectRootNotFoundError


class DummyPolicy:
    """Simple scope policy used in tests.

    The policy mirrors the old behaviour of :class:`IniFileBackend` by storing
    user configuration under ``user_dir/<provider>`` and project configuration
    directly under ``project_dir``.
    """

    def __init__(self, user_dir: Path, project_dir: Path | None, host: str = "host"):
        self.user_dir = Path(user_dir)
        self.project_dir = Path(project_dir) if project_dir is not None else None
        self.host = host

    def precedence(self, *, read: bool = False):
        return (
            "env",
            "project-local",
            "project",
            "user-local",
            "user",
            "default",
            "core",
        )

    def path(self, scope: str, provider_id: str, *, auto: bool = False) -> Path:
        pid = provider_id
        if scope == "user":
            base = self.user_dir / pid
            base.mkdir(parents=True, exist_ok=True)
            name = (
                f"settings-local-{self.host}.ini" if pid == "user-custom" else "settings.ini"
            )
            return base / name
        if scope == "user-local":
            base = self.user_dir / pid
            base.mkdir(parents=True, exist_ok=True)
            return base / f"settings-local-{self.host}.ini"
        if scope == "project":
            if self.project_dir is None:
                raise ProjectRootNotFoundError("No project directory configured")
            base = self.project_dir
            base.mkdir(parents=True, exist_ok=True)
            return base / "settings.ini"
        if scope == "project-local":
            if self.project_dir is None:
                raise ProjectRootNotFoundError("No project directory configured")
            base = self.project_dir
            base.mkdir(parents=True, exist_ok=True)
            return base / f"settings-local-{self.host}.ini"
        raise ValueError(f"unknown scope {scope!r}")

    def allows(self, scope: str) -> bool:  # pragma: no cover - trivial
        return scope in {"user", "user-local", "project", "project-local", "default"}

    def machine_scopes(self):  # pragma: no cover - trivial
        return ["user-local", "project-local"]
