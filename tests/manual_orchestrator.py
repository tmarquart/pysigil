"""Manual end-to-end exercises for the orchestrator.

Running this module as a script will create temporary configuration files
and demonstrate some of the key features of :class:`~pysigil.orchestrator.Orchestrator`.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from pysigil.orchestrator import InMemorySpecBackend, Orchestrator
from pysigil.settings_metadata import IniFileBackend


def manual_demo() -> None:
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        backend = IniFileBackend(
            user_dir=base / "user",
            project_dir=base / "proj",
            host="host",
        )
        spec_backend = InMemorySpecBackend()
        orch = Orchestrator(spec_backend, backend)

        orch.register_provider("demo", title="Demo")
        orch.add_field("demo", key="greeting", type="string", label="Greeting")
        orch.set_value("demo", "greeting", "hello")
        print("Effective after set:", orch.get_effective("demo"))

        orch.edit_field("demo", "greeting", new_key="salutation")
        print("After rename:", orch.get_effective("demo"))

        file_path = base / "user" / "demo" / "settings.ini"
        print("Stored file contents:\n", file_path.read_text())

        orch.delete_field("demo", "salutation", remove_values=True)
        print("After delete:", orch.get_effective("demo"))


if __name__ == "__main__":  # pragma: no cover - manual execution
    manual_demo()

