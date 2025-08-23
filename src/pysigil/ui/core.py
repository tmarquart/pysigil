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

from .. import api

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
    is_dirty_spec: bool = False
    is_dirty_values: bool = False
    project_detected: bool = True


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

    def list_providers(self) -> list[str]:
        return api.providers()

    def select_provider(self, pid: str) -> api.ProviderInfo:
        return api.get_provider(pid)

    def get_fields(self, pid: str) -> list[api.FieldInfo]:
        return api.handle(pid).fields()

    def get_effective(self, pid: str) -> Dict[str, api.ValueInfo]:
        return api.handle(pid).effective()

    def add_field(
        self,
        pid: str,
        key: str,
        type: str,
        *,
        label: str | None = None,
        description: str | None = None,
        init_scope: Literal["user", "project"] | None = "user",
    ) -> api.FieldInfo:
        return api.handle(pid).add_field(
            key,
            type,
            label=label,
            description=description,
            init_scope=init_scope,
        )

    def set_value(
        self,
        pid: str,
        key: str,
        value: Any,
        *,
        scope: Literal["user", "project"] = "user",
    ) -> None:
        api.handle(pid).set(key, value, scope=scope)

    def clear_value(
        self,
        pid: str,
        key: str,
        *,
        scope: Literal["user", "project"] = "user",
    ) -> None:
        api.handle(pid).clear(key, scope=scope)

    def init(self, pid: str, scope: Literal["user", "project"]) -> None:
        api.handle(pid).init(scope)

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
    ) -> None:
        self.state = AppState()
        self.service = service or ProvidersService()
        self.events = EventBus()
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
            with self._lock:
                self.state.provider_id = pid
                self.state.provider_info = info
                self.state.fields = fields
                self.state.values = values
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
            with self._lock:
                self.state.provider_info = info
                self.state.fields = fields
                self.state.values = values
            self.events.emit_state(self.state)

        return self.run_async(_task)

    def save_value(
        self, key: str, value: Any, *, scope: Literal["user", "project"] = "user"
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            self.service.set_value(pid, key, value, scope=scope)
            val = self.service.get_effective(pid).get(key)
            if val is not None:
                with self._lock:
                    self.state.values[key] = val
            self.events.emit_state(self.state)

        return self.run_async(_task)

    def clear_value(
        self, key: str, *, scope: Literal["user", "project"] = "user"
    ) -> Future[None]:
        pid = self.state.provider_id
        if pid is None:
            raise RuntimeError("no provider selected")

        def _task() -> None:
            self.service.clear_value(pid, key, scope=scope)
            with self._lock:
                self.state.values.pop(key, None)
            self.events.emit_state(self.state)

        return self.run_async(_task)


__all__ = [
    "AppCore",
    "AppState",
    "EventBus",
    "ProvidersService",
]
