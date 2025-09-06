"""Framework agnostic GUI core.

The :mod:`pysigil.ui.core` module exposes the minimal pieces required to
build a graphical user interface on top of :mod:`pysigil.api`.  The code
here purposefully knows nothing about any widget toolkit; instead it is
responsible for keeping track of application state, delegating all heavy
lifting to :mod:`pysigil.api` and notifying interested parties about
state changes via a tiny callback based event system.

The intention is that concrete front-ends – for instance a tkinter based
one – bind to the callbacks exposed here.  Replacing the front-end should
only require reimplementing the view layer while this module can be
reused unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Protocol
from concurrent.futures import ThreadPoolExecutor, Future
import threading
from pathlib import Path

from .. import api, config, paths

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AppState:
    """In-memory representation of the UI state."""

    provider_id: str | None = None
    provider_info: api.ProviderInfo | None = None
    fields: list[api.FieldInfo] = field(default_factory=list)
    values: Dict[str, api.ValueInfo] = field(default_factory=dict)
    active_tab: Literal["overview", "user", "project"] = "overview"
    active_scope: Literal["user", "project"] = "user"
    host_id: str = config.host_id()
    project_root: Path | None = None
    is_dirty_spec: bool = False
    is_dirty_values: bool = False
    project_detected: bool = True
    author_mode: bool = False


# ---------------------------------------------------------------------------
# Event handling
# ---------------------------------------------------------------------------


class EventBus:
    """Simple callback based pub/sub system."""

    def __init__(self) -> None:
        self.on_state_changed: list[Callable[[AppState], None]] = []
        self.on_error: list[Callable[[str], None]] = []
        self.on_toast: list[Callable[[str, str], None]] = []
        self.on_confirm: list[Callable[[str, str], bool]] = []
        self.on_progress: list[Callable[[bool], None]] = []

    # Emit helpers -----------------------------------------------------
    def emit_state(self, state: AppState) -> None:
        for cb in list(self.on_state_changed):
            cb(state)

    def emit_error(self, msg: str) -> None:
        for cb in list(self.on_error):
            cb(msg)

    def emit_toast(self, msg: str, level: str = "info") -> None:
        for cb in list(self.on_toast):
            cb(msg, level)

    def emit_progress(self, started: bool) -> None:
        for cb in list(self.on_progress):
            cb(started)


# ---------------------------------------------------------------------------
# Service façade (thin wrapper over :mod:`pysigil.api`)
# ---------------------------------------------------------------------------


class ProvidersService:
    """Lightweight façade over :mod:`pysigil.api`.

    The service performs no caching; callers are expected to cache data in
    :class:`AppState` if necessary.
    """

    def __init__(self, *, author_mode: bool = False) -> None:
        self.author_mode = author_mode

    def list_providers(self) -> list[str]:
        return api.providers()

    def select_provider(self, pid: str) -> api.ProviderInfo:
        return api.get_provider(pid)

    def get_fields(self, pid: str) -> list[api.FieldInfo]:
        return api.handle(pid).fields()

    def get_effective(self, pid: str) -> Dict[str, api.ValueInfo]:
        return api.handle(pid).effective()

    def get_layers(self, pid: str) -> Dict[str, Dict[str, api.ValueInfo | None]]:
        return api.handle(pid).layers()

    def add_field(
        self,
        pid: str,
        key: str,
        type: str,
        *,
        label: str | None = None,
        description: str | None = None,
        options: Dict[str, Any] | None = None,
        init_scope: Literal["user", "project"] | None = "user",
    ) -> api.FieldInfo:
        return api.handle(pid).add_field(
            key,
            type,
            label=label,
            description=description,
            options=options,
            init_scope=init_scope,
        )

    def set_value(
        self,
        pid: str,
        key: str,
        value: Any,
        *,
        scope: Literal["user", "project", "default"] = "user",
    ) -> None:
        if scope == "default":
            if not self.author_mode:
                raise PermissionError("default scope is read-only")
            api.handle(pid)._manager().set(  # type: ignore[attr-defined]
                key, value, scope="default"
            )
            return
        api.handle(pid).set(key, value, scope=scope)

    def clear_value(
        self,
        pid: str,
        key: str,
        *,
        scope: Literal["user", "project", "default"] = "user",
    ) -> None:
        if scope == "default":
            if not self.author_mode:
                raise PermissionError("default scope is read-only")
            api.handle(pid)._manager().clear(  # type: ignore[attr-defined]
                key, scope="default"
            )
            return
        api.handle(pid).clear(key, scope=scope)

    def init(self, pid: str, scope: Literal["user", "project"]) -> None:
        api.handle(pid).init(scope)

    def edit_field(
        self,
        pid: str,
        key: str,
        *,
        new_key: str | None = None,
        new_type: str | None = None,
        label: str | None = None,
        description: str | None = None,
        options: Dict[str, Any] | None = None,
        on_type_change: Literal["convert", "clear"] = "convert",
        migrate_scopes: tuple[Literal["user", "project"], ...] = ("user",),
    ) -> api.FieldInfo:
        return api.handle(pid).edit_field(
            key,
            new_key=new_key,
            new_type=new_type,
            label=label,
            description=description,
            options=options,
            on_type_change=on_type_change,
            migrate_scopes=migrate_scopes,
        )

    def delete_field(
        self,
        pid: str,
        key: str,
        *,
        remove_values: bool = False,
        scopes: tuple[Literal["user", "project"], ...] = ("user",),
    ) -> None:
        api.handle(pid).delete_field(key, remove_values=remove_values, scopes=scopes)

    def adopt_untracked(self, pid: str, mapping: Dict[str, str]) -> list[api.FieldInfo]:
        return api.handle(pid).adopt_untracked(mapping)

    def open_folder(self, pid: str, scope: Literal["user", "project"]) -> Path:
        path = config.open_scope(pid, scope)
        self._open_path(path)
        return path

    def open_file(self, pid: str, scope: Literal["user", "project"]) -> Path:
        path = config.init_config(pid, scope)
        self._open_path(path)
        return path

    def ensure_gitignore(self) -> Path:
        return config.ensure_gitignore()

    # -- helpers -----------------------------------------------------
    @staticmethod
    def _open_path(path: Path) -> None:
        try:  # pragma: no cover - platform specific
            import os, subprocess, sys

            if sys.platform.startswith("darwin"):
                subprocess.run(["open", str(path)], check=False)
            elif os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            pass

    def export_spec(self, pid: str) -> None:  # pragma: no cover - thin pass through
        api.handle(pid).export_spec()

    def reload_spec(self, pid: str) -> api.ProviderInfo:
        return api.handle(pid).info()


# ---------------------------------------------------------------------------
# App core / command helpers
# ---------------------------------------------------------------------------


class AppCore:
    """Mediator between the view and :class:`ProvidersService`.

    It keeps the current :class:`AppState` and exposes a small selection of
    command methods which operate on the service.  All operations involving
    the service are executed in a thread pool in order to avoid blocking the
    UI thread in front-ends such as tkinter.
    """

    def __init__(
        self,
        service: ProvidersService | None = None,
        *,
        executor: ThreadPoolExecutor | None = None,
        author_mode: bool = False,
    ) -> None:
        self.state = AppState(author_mode=author_mode)
        self.service = service or ProvidersService(author_mode=author_mode)
        self.events = EventBus()
        self.orchestrator = api._ORCH
        self._executor = executor or ThreadPoolExecutor(max_workers=4)
        self._lock = threading.Lock()

    # --- concurrency -------------------------------------------------
    def run_async(self, fn: Callable[[], Any]) -> Future[Any]:
        """Run ``fn`` in the thread pool and return the future."""

        def runner() -> Any:
            try:
                self.events.emit_progress(True)
                return fn()
            finally:
                self.events.emit_progress(False)

        return self._executor.submit(runner)

    # --- commands ----------------------------------------------------
    def select_provider(self, pid: str) -> Future[None]:
        """Load provider metadata and effective values."""

        def _task() -> None:
            info = self.service.select_provider(pid)
            fields = self.service.get_fields(pid)
            values = self.service.get_effective(pid)
            try:
                root = paths.project_root()
                detected = True
            except Exception:
                root = None
                detected = False
            with self._lock:
                self.state.provider_id = pid
                self.state.provider_info = info
                self.state.fields = fields
                self.state.values = values
                self.state.project_root = root
                self.state.project_detected = detected
            self.events.emit_state(self.state)

        return self.run_async(_task)

    def refresh(self) -> Future[None]:
        """Refresh fields and values for the current provider."""

        pid = self.state.provider_id
        if pid is None:  # nothing to do
            future: Future[None] = Future()
            future.set_result(None)
            return future

        def _task() -> None:
            info = self.service.reload_spec(pid)
            fields = self.service.get_fields(pid)
            values = self.service.get_effective(pid)
            try:
                root = paths.project_root()
                detected = True
            except Exception:
                root = None
                detected = False
            with self._lock:
                self.state.provider_info = info
                self.state.fields = fields
                self.state.values = values
                self.state.project_root = root
                self.state.project_detected = detected
            self.events.emit_state(self.state)

        return self.run_async(_task)

    def save_value(
        self, key: str, value: Any, *, scope: Literal["user", "project"] = "user"
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.set_value(pid, key, value, scope=scope)
                val = self.service.get_effective(pid).get(key)
                if val is not None:
                    with self._lock:
                        self.state.values[key] = val
                self.events.emit_toast("Saved", "info")
                self.events.emit_state(self.state)
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def clear_value(
        self, key: str, *, scope: Literal["user", "project"] = "user"
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.clear_value(pid, key, scope=scope)
                with self._lock:
                    self.state.values.pop(key, None)
                self.events.emit_toast("Cleared", "info")
                self.events.emit_state(self.state)
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def init_scope(self, scope: Literal["user", "project"]) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.init(pid, scope)
                self.events.emit_toast(f"Initialized {scope} scope", "info")
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def open_folder(self, scope: Literal["user", "project"]) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                path = self.service.open_folder(pid, scope)
                self.events.emit_toast(str(path), "info")
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def open_file(self, scope: Literal["user", "project"]) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                path = self.service.open_file(pid, scope)
                self.events.emit_toast(str(path), "info")
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def add_gitignore(self) -> Future[None]:
        def _task() -> None:
            try:
                path = self.service.ensure_gitignore()
                self.events.emit_toast(str(path), "info")
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def set_active_scope(self, scope: Literal["user", "project"]) -> None:
        with self._lock:
            self.state.active_scope = scope
        self.events.emit_state(self.state)

    def add_field(
        self,
        key: str,
        type: str,
        *,
        label: str | None = None,
        description: str | None = None,
        init_scope: Literal["user", "project"] | None = "user",
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.add_field(
                    pid,
                    key,
                    type,
                    label=label,
                    description=description,
                    init_scope=init_scope,
                )
                self.refresh()
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def edit_field(
        self,
        key: str,
        *,
        new_key: str | None = None,
        new_type: str | None = None,
        label: str | None = None,
        description: str | None = None,
        on_type_change: Literal["convert", "clear"] = "convert",
        migrate_scopes: tuple[Literal["user", "project"], ...] = ("user",),
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.edit_field(
                    pid,
                    key,
                    new_key=new_key,
                    new_type=new_type,
                    label=label,
                    description=description,
                    on_type_change=on_type_change,
                    migrate_scopes=migrate_scopes,
                )
                self.refresh()
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def delete_field(
        self,
        key: str,
        *,
        remove_values: bool = False,
        scopes: tuple[Literal["user", "project"], ...] = ("user",),
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.delete_field(
                    pid, key, remove_values=remove_values, scopes=scopes
                )
                self.refresh()
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)

    def adopt_untracked(self, mapping: Dict[str, str]) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            try:
                self.service.adopt_untracked(pid, mapping)
                self.refresh()
            except Exception as exc:
                self.events.emit_error(str(exc))
                self.events.emit_toast(str(exc), "error")

        return self.run_async(_task)


__all__ = [
    "AppCore",
    "AppState",
    "EventBus",
    "ProvidersService",
]
