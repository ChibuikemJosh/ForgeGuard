"""Truthful, privacy-safe step trace for investigations."""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.schemas.security_investigation import InvestigationStep

MAX_STEPS = 200


class InvestigationCancelled(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InvestigationRecorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._steps: list[InvestigationStep] = []
        self._started: dict[str, float] = {}
        self._overflow = 0
        self._overflow_id: str | None = None
        self.cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self.cancelled = True

    def check_cancelled(self) -> None:
        with self._lock:
            cancelled = self.cancelled
        if cancelled:
            raise InvestigationCancelled("Investigation was cancelled.")

    def start(self, kind, label, tool_name=None) -> str:
        step_id = f"step-{uuid.uuid4().hex[:12]}"
        with self._lock:
            if len(self._steps) >= MAX_STEPS:
                self._overflow += 1
                label_overflow = f"+{self._overflow} more steps"
                if self._overflow_id:
                    for s in self._steps:
                        if s.step_id == self._overflow_id:
                            s.label = label_overflow
                else:
                    self._overflow_id = step_id
                    self._steps.append(InvestigationStep(step_id=step_id, kind=kind, label=label_overflow, status="skipped", started_at=_now()))
                return self._overflow_id
            self._steps.append(InvestigationStep(step_id=step_id, kind=kind, label=str(label)[:300], tool_name=tool_name, status="running", started_at=_now()))
            self._started[step_id] = time.monotonic()
        return step_id

    def finish(self, step_id, status="ok", message=None) -> None:
        with self._lock:
            for s in self._steps:
                if s.step_id == step_id:
                    s.status = status  # type: ignore[assignment]
                    s.message = str(message)[:300] if message else None
                    started = self._started.pop(step_id, None)
                    s.duration_ms = int((time.monotonic() - started) * 1000) if started is not None else None
                    break

    def snapshot(self) -> list[InvestigationStep]:
        with self._lock:
            return [s.model_copy(deep=True) for s in self._steps]

    @contextmanager
    def step(self, kind, label, tool_name=None):
        step_id = self.start(kind, label, tool_name)
        try:
            yield step_id
        except Exception as error:
            self.finish(step_id, "failed", str(error)[:300])
            raise
        else:
            self.finish(step_id, "ok")


try:
    from langchain_core.callbacks import BaseCallbackHandler
except Exception:  # pragma: no cover
    BaseCallbackHandler = object  # type: ignore


class TraceCallbackHandler(BaseCallbackHandler):  # type: ignore[valid-type,misc]
    raise_error = True

    def __init__(self, recorder: InvestigationRecorder) -> None:
        self.recorder = recorder
        self._runs: dict[str, str] = {}

    def _model_label(self, kwargs) -> str:
        name = None
        try:
            inv = kwargs.get("invocation_params") or {}
            name = inv.get("model") or inv.get("model_name")
        except Exception:
            name = None
        return f"Muse analysis ({name or 'model'})"

    def on_chat_model_start(self, serialized=None, messages=None, *, run_id=None, **kwargs):
        self.recorder.check_cancelled()
        sid = self.recorder.start("model", self._model_label(kwargs))
        if run_id is not None:
            self._runs[str(run_id)] = sid

    def on_llm_start(self, serialized=None, prompts=None, *, run_id=None, **kwargs):
        self.recorder.check_cancelled()
        sid = self.recorder.start("model", self._model_label(kwargs))
        if run_id is not None:
            self._runs[str(run_id)] = sid

    def on_llm_end(self, response=None, *, run_id=None, **kwargs):
        sid = self._runs.pop(str(run_id), None)
        if sid:
            self.recorder.finish(sid, "ok")

    def on_llm_error(self, error=None, *, run_id=None, **kwargs):
        sid = self._runs.pop(str(run_id), None)
        if sid:
            self.recorder.finish(sid, "failed", str(error)[:300] if error else None)

    def on_tool_start(self, serialized=None, input_str=None, *, run_id=None, inputs=None, **kwargs):
        self.recorder.check_cancelled()
        tool_name = (serialized or {}).get("name") if isinstance(serialized, dict) else None
        data = inputs if isinstance(inputs, dict) else {}
        fp, ln = data.get("file_path"), data.get("line_number")
        label = f"Looking up graph nodes at {fp}:{ln}" if fp and ln else f"Calling {tool_name or 'tool'}"
        sid = self.recorder.start("tool", label, tool_name=tool_name)
        if run_id is not None:
            self._runs[str(run_id)] = sid

    def on_tool_end(self, output=None, *, run_id=None, **kwargs):
        sid = self._runs.pop(str(run_id), None)
        if sid:
            msg = f"{len(output)} result(s)" if isinstance(output, list) else None
            self.recorder.finish(sid, "ok", msg)

    def on_tool_error(self, error=None, *, run_id=None, **kwargs):
        sid = self._runs.pop(str(run_id), None)
        if sid:
            self.recorder.finish(sid, "failed", str(error)[:300] if error else None)
