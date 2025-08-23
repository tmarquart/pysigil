"""Manual end-to-end exercises for the orchestrator.

Running this module as a script will create configuration files in the
current user's configuration directory and demonstrate several features of
the :class:`~pysigil.orchestrator.Orchestrator`.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from pysigil.orchestrator import Orchestrator
from pysigil.paths import user_config_dir

#C:\Users\tmarq\AppData\Local\sigil\sigil\demo

def manual_demo() -> None:
    """Showcase provider registration and modification."""

    user_dir = user_config_dir("sigil")
    with TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "proj"
        orch = Orchestrator(
            user_dir=user_dir,
            project_dir=project_dir,
            host="host",
        )

        # Register a provider (project) and add three fields
        orch.register_provider("demo", title="Demo Project")
        orch.add_field("demo", key="alpha", type="string", label="Alpha")
        orch.add_field("demo", key="beta", type="integer", label="Beta")
        orch.add_field("demo", key="gamma", type="boolean", label="Gamma")

        # Set some values in user scope
        orch.set_value("demo", "alpha", "hello")
        orch.set_value("demo", "beta", 42)
        orch.set_value("demo", "gamma", True)

        #orch.set_value("demo", "gamma", "NOT A BOOL") #errors as expected
        print("Effective after set:", orch.get_effective("demo"))

        # Edit one field and delete another
        orch.edit_field("demo", "beta", new_key="delta")
        print("After field edit:", orch.get_effective("demo"))
        orch.delete_field("demo", "gamma", remove_values=True)
        print("After delete:", orch.get_effective("demo"))

        # Edit the provider itself
        orch.edit_provider("demo", title="Demo Project Updated")
        spec = orch.spec_backend.get_spec("demo")
        print("Updated provider title:", spec.title)

        user_file = user_dir / "demo" / "settings.ini"
        spec_file = user_dir / "demo" / "metadata.ini"
        print("User file contents:\n", user_file.read_text())
        print("Metadata file contents:\n", spec_file.read_text())


if __name__ == "__main__":  # pragma: no cover - manual execution
    manual_demo()

