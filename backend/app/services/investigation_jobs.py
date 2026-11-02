"""Background investigation jobs polled by the frontend."""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.schemas.security_investigation import InvestigationResult, InvestigationStatus
from app.services.investigation_trace import InvestigationRecorder


class JobConflictError(Exception):
    pass


class InvestigationJobManager:
    def __init__(self, runner):
        """runner(project, index, graph, rule, recorder, investigation_id) -> InvestigationResult"""
        self._runner = runner
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}

    def _cleanup(self):
        now = time.time()
        with self._lock:
            expired = [k for k, j in self._jobs.items() if j.get("finished_at") and now - j["finished_at"] > 3600]
            for k in expired:
                del self._jobs[k]
            while len(self._jobs) > 100:
                oldest = min(self._jobs, key=lambda k: self._jobs[k]["created_at"])
                del self._jobs[oldest]

    def start(self, project, index, graph, rule, client_ip) -> str:
        self._cleanup()
        with self._lock:
            for j in self._jobs.values():
                if j["client_ip"] == client_ip and j["result"] is None:
                    raise JobConflictError("An investigation is already running for this browser. Wait for it to finish or cancel it.")
            investigation_id = f"investigation-{uuid.uuid4().hex[:12]}"
            recorder = InvestigationRecorder()
            job = {"project_id": project.project_id, "rule_id": rule.rule_id, "recorder": recorder, "future": None, "result": None, "client_ip": client_ip, "created_at": time.time(), "finished_at": None, "project": project, "rule": rule}
            self._jobs[investigation_id] = job

        def _run():
            try:
                result = self._runner(project, index, graph, rule, recorder, investigation_id)
            except Exception as error:  # runner normally returns failed results
                result = InvestigationResult(investigation_id=investigation_id, project_id=project.project_id, rule_id=rule.rule_id, status=InvestigationStatus.FAILED, errors=[str(error)[:300]], summary="Investigation failed.", steps=recorder.snapshot())
            with self._lock:
                job["result"] = result
                job["finished_at"] = time.time()
            return result

        with self._lock:
            job["future"] = self._executor.submit(_run)
        return investigation_id

    def get(self, investigation_id: str) -> InvestigationResult | None:
        with self._lock:
            job = self._jobs.get(investigation_id)
            if job is None:
                return None
            result, recorder, pid, rid = job["result"], job["recorder"], job["project_id"], job["rule_id"]
        if result is not None:
            return result
        return InvestigationResult(investigation_id=investigation_id, project_id=pid, rule_id=rid, status=InvestigationStatus.RUNNING, findings=[], errors=[], summary="Investigation in progress.", steps=recorder.snapshot())

    def cancel(self, investigation_id: str) -> InvestigationResult | None:
        with self._lock:
            job = self._jobs.get(investigation_id)
            if job is None:
                return None
            recorder = job["recorder"]
        recorder.cancel()
        return self.get(investigation_id)
