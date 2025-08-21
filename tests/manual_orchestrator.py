"""Manual end-to-end exercises for the orchestrator.

Running this module as a script will create configuration files in the
current user's configuration directory and demonstrate several features of
the :class:`~pysigil.orchestrator.Orchestrator`.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from pysigil.orchestrator import InMemorySpecBackend, Orchestrator
from pysigil.paths import user_config_dir
from pysigil.settings_metadata import IniFileBackend


def manual_demo() -> None:
    """Showcase provider registration and modification."""

    user_dir = user_config_dir("sigil")
    with TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "proj"
        backend = IniFileBackend(
            user_dir=user_dir,
            project_dir=project_dir,
            host="host",
        )
        spec_backend = InMemorySpecBackend()
        orch = Orchestrator(spec_backend, backend)

        # Register a provider (project) and add three fields
        orch.register_provider("demo", title="Demo Project")
        orch.add_field("demo", key="alpha", type="string", label="Alpha")
        orch.add_field("demo", key="beta", type="integer", label="Beta")
        orch.add_field("demo", key="gamma", type="boolean", label="Gamma")

        # Set some values in user and project scopes
        orch.set_value("demo", "alpha", "hello")
        orch.set_value("demo", "beta", 42, scope="project")
        orch.set_value("demo", "gamma", True)
        print("Effective after set:", orch.get_effective("demo"))

        # Edit one field and delete another
        orch.edit_field("demo", "beta", new_key="delta")
        print("After field edit:", orch.get_effective("demo"))
        orch.delete_field("demo", "gamma", remove_values=True)
        print("After delete:", orch.get_effective("demo"))

        # Edit the provider itself
        orch.edit_provider("demo", title="Demo Project Updated")
        spec = spec_backend.get_spec("demo")
        print("Updated provider title:", spec.title)

        user_file = user_dir / "demo" / "settings.ini"
        project_file = project_dir / "demo" / "settings.ini"
        print("User file contents:\n", user_file.read_text())
        print("Project file contents:\n", project_file.read_text())


if __name__ == "__main__":  # pragma: no cover - manual execution
    manual_demo()

