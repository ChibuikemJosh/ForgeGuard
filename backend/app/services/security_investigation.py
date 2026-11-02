# test
from __future__ import annotations

import inspect
import os
import uuid

from app.schemas.code_intelligence import CodeIndex
from app.schemas.security import SecurityRule, SourceReference
from app.schemas.security_investigation import (
    EvidenceItem,
    EvidenceType,
    FindingStatus,
    InvestigationFinding,
    InvestigationResult,
    InvestigationStatus,
)
from app.schemas.source_graph import SourceGraph
from app.services.evidence_validation import EvidenceValidator
from app.services.investigation_trace import InvestigationCancelled, InvestigationRecorder, TraceCallbackHandler
from app.services.project_workspace import ProjectReference, WorkspaceService
from app.services.source_graph_lookup import match_nodes_at_location
# Ram's agent is imported lazily so this module can be imported without the
# optional LangChain dependency unless an investigation actually runs.


class SecurityInvestigationService:
    def __init__(self, workspace, agent=None):
        self.workspace = workspace
        self.agent = agent

    def investigate(self, project, index, graph, rule, agent=None, session_id=None, recorder: InvestigationRecorder | None = None):
        if agent is None:
            if self.agent is None:
                from app.services.violations_finder_agent import ViolationsFinderAgent

                self.agent = ViolationsFinderAgent()
            agent = self.agent
        investigation_id = session_id or f"investigation-{uuid.uuid4().hex[:12]}"
        from app.services.violations_finder_agent import (
            AgentConfigurationError,
            AgentResponseError,
            ProjectFolderError,
        )

        if recorder is None:
            recorder = InvestigationRecorder()
        project_folder = str(self.workspace.project_root(project.project_id))
        context_files = self._plan_context_files(index, graph, rule)
        details = self._rule_text(rule, index, graph, context_files)
        try:
            locations = self._find_locations(
                agent,
                details,
                project_folder,
                investigation_id,
                context_files,
                project_id=project.project_id,
            )
            if not locations and self._max_follow_up_rounds() > 0:
                locations = self._find_locations(
                    agent,
                    details
                    + "\nEvidence was insufficient on the first pass. "
                    "Perform one focused follow-up over the planned context.",
                    project_folder,
                    investigation_id,
                    context_files,
                    project_id=project.project_id,
                    follow_up=True,
                )
        except AgentConfigurationError as error:
            if agent_step:
                recorder.finish(agent_step, "failed", str(error)[:300])
            recorder.finish(planning_id, "failed", str(error)[:300])
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="Investigation could not run because the AI provider is not configured.",
                truncated=getattr(agent, "last_truncated", False),
                steps=recorder.snapshot(),
            )
        except ProjectFolderError as error:
            if agent_step:
                recorder.finish(agent_step, "failed", str(error)[:300])
            recorder.finish(planning_id, "failed", str(error)[:300])
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                truncated=getattr(agent, "last_truncated", False),
                steps=recorder.snapshot(),
            )
        except AgentResponseError as error:
            if agent_step:
                recorder.finish(agent_step, "failed", str(error)[:300])
            recorder.finish(planning_id, "failed", str(error)[:300])
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="The agent response could not be parsed into locations.",
                truncated=getattr(agent, "last_truncated", False),
                steps=recorder.snapshot(),
            )
        except Exception as error:
            if isinstance(error, InvestigationCancelled):
                return InvestigationResult(investigation_id=investigation_id, project_id=project.project_id, rule_id=rule.rule_id, status=InvestigationStatus.CANCELLED, summary="Investigation was cancelled.", truncated=getattr(agent, "last_truncated", False), steps=recorder.snapshot())
            if agent_step:
                recorder.finish(agent_step, "failed", str(error)[:300])
            recorder.finish(planning_id, "failed", str(error)[:300])
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[f"Investigation failed: {error}"],
                truncated=getattr(agent, "last_truncated", False),
                steps=recorder.snapshot(),
            )

        locations = locations or []
        locations = self._deduplicate_locations(locations)
        truncated = getattr(agent, "last_truncated", False)
        validator = EvidenceValidator(self.workspace, project.project_id, index, graph)
        evidence_items = []
        affected_files = []
        affected_symbols = []
        related_nodes = []
        errors = []
        self._mapping_errors = []
        self._recorder = recorder
        validation_id = recorder.start("validation", f"Validating {len(locations)} proposed locations against source")
        for location in locations:
            try:
                recorder.check_cancelled()
            except InvestigationCancelled:
                recorder.finish(validation_id, "failed", "Investigation was cancelled.")
                return InvestigationResult(investigation_id=investigation_id, project_id=project.project_id, rule_id=rule.rule_id, status=InvestigationStatus.CANCELLED, summary="Investigation was cancelled.", truncated=truncated, steps=recorder.snapshot())
            try:
                item = self._validate_location(project, index, graph, validator, location)
            except Exception as error:
                errors.append(f"Invalid agent location: {error}")
                continue
            evidence_items.append(item)
            if item.status.value == "valid":
                if item.file_path not in affected_files:
                    affected_files.append(item.file_path)
                if item.symbol_id and item.symbol_id not in affected_symbols:
                    affected_symbols.append(item.symbol_id)
                for node in item.related_graph_nodes:
                    if node not in related_nodes:
                        related_nodes.append(node)

        valid_items = [item for item in evidence_items if item.status.value == "valid"]
        recorder.finish(validation_id, "ok", f"{len(valid_items)} valid, {len(evidence_items) - len(valid_items)} rejected")
        errors.extend(getattr(self, "_mapping_errors", []))
        if not locations:
            status = InvestigationStatus.INCONCLUSIVE
        elif valid_items:
            status = InvestigationStatus.COMPLETED
        else:
            status = InvestigationStatus.INCONCLUSIVE

        finding_status = FindingStatus.POTENTIAL if valid_items else FindingStatus.INCONCLUSIVE
        findings = []
        if locations:
            findings.append(
                InvestigationFinding(
                    finding_id=f"finding-{uuid.uuid4().hex[:8]}",
                    rule_id=rule.rule_id,
                    title=f"Potential violation of {rule.title or getattr(rule, 'name', None) or rule.rule_id}",
                    description=(
                        "The Violations Finder Agent identified source locations that may "
                        "violate the supplied security rule."
                    ),
                    severity=rule.severity,
                    confidence=0.5,
                    status=finding_status,
                    affected_files=affected_files,
                    affected_symbols=affected_symbols,
                    related_graph_nodes=related_nodes,
                    evidence=evidence_items,
                    reasoning=(
                        f"The agent returned {len(locations)} location(s); "
                        f"{len(valid_items)} passed backend evidence validation."
                    ),
                    recommended_remediation=(
                        "Review the identified code paths and enforce the security rule."
                    ),
                )
            )

        if evidence_items and not valid_items:
            errors.append("Agent-proposed locations did not pass evidence validation.")
        if getattr(agent, "last_truncated", False):
            errors.append(
                "Project file listing was truncated; not all Python files were sent to the model."
            )
        return InvestigationResult(
            investigation_id=investigation_id,
            project_id=project.project_id,
            rule_id=rule.rule_id,
            status=status,
            findings=findings,
            errors=errors,
            truncated=truncated,
            steps=recorder.snapshot(),
            summary=(
                f"Investigated {len(index.files)} files; agent returned "
                f"{len(locations)} location(s), {len(valid_items)} validated."
                + (" Project context was truncated." if truncated else "")
            ),
        )

    @staticmethod
    def _deduplicate_locations(locations):
        unique = []
        seen = set()
        for location in locations:
            key = (
                getattr(location, "filename", None),
                getattr(location, "linenumber", None),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(location)
        return unique

    @staticmethod
    def _find_locations(
        agent,
        details,
        project_folder,
        investigation_id,
        context_files,
        follow_up=False,
        project_id=None,
    ):
        parameters = inspect.signature(agent.find_violations).parameters
        kwargs = {}
        if "context_files" in parameters:
            kwargs["context_files"] = context_files
        if "follow_up" in parameters:
            kwargs["follow_up"] = follow_up
        if "project_id" in parameters:
            kwargs["project_id"] = project_id
        return agent.find_violations(
            details,
            project_folder,
            investigation_id,
            **kwargs,
        )

    @staticmethod
    def _max_follow_up_rounds() -> int:
        try:
            configured = int(
                os.environ.get("FORGE_INVESTIGATION_MAX_FOLLOW_UP_ROUNDS", "1")
            )
        except ValueError:
            configured = 1
        return max(0, min(configured, 1))

    @staticmethod
    def _plan_context_files(index, graph, rule):
        """Select a bounded, graph-connected source context before model analysis."""
        python_files = set(index.files)
        terms = " ".join(
            str(value or "")
            for value in (
                rule.rule_id,
                rule.title,
                rule.invariant,
                rule.description,
                rule.category,
                rule.expected_property,
                *rule.concepts,
                *rule.indicators,
            )
        ).lower()
        keywords = {
            token.strip("_-")
            for token in terms.replace("/", " ").replace(".", " ").split()
            if len(token.strip("_-")) >= 4
        }
        selected = {
            node.file_path
            for node in graph.nodes
            if node.file_path in python_files
            and any(
                keyword in " ".join(
                    filter(
                        None,
                        (
                            node.name,
                            node.qualified_name,
                            node.module,
                            node.file_path,
                        ),
                    )
                ).lower()
                for keyword in keywords
            )
        }
        if not selected:
            return python_files

        node_files = {
            node.id: node.file_path
            for node in graph.nodes
            if node.file_path in python_files
        }
        selected_node_ids = {
            node.id for node in graph.nodes if node.file_path in selected
        }
        for edge in graph.edges:
            if edge.source in selected_node_ids and edge.target in node_files:
                selected.add(node_files[edge.target])
            if edge.target in selected_node_ids and edge.source in node_files:
                selected.add(node_files[edge.source])
        return selected

    def _rule_text(self, rule, index=None, graph=None, context_files=None):
        title = rule.title or getattr(rule, "name", None) or rule.rule_id
        parts = [title]
        if rule.invariant:
            parts.append(rule.invariant)
        if rule.description:
            parts.append(rule.description)
        if rule.expected_property:
            parts.append(f"Expected property: {rule.expected_property}")
        if rule.guidance:
            parts.append(f"Guidance: {rule.guidance}")
        if rule.category:
            parts.append(f"Category: {rule.category}")
        if rule.concepts:
            parts.append(f"Relevant concepts: {', '.join(rule.concepts)}")
        if rule.indicators:
            parts.append(f"Indicators to examine: {', '.join(rule.indicators)}")
        if rule.examples:
            parts.append("Examples: " + "; ".join(rule.examples))
        if graph is not None:
            parts.append(
                "Backend SourceGraph context (structural observations only; "
                "do not treat these as semantic proof):"
            )
            for node in graph.nodes:
                if node.file_path is not None and (
                    context_files is None or node.file_path in context_files
                ):
                    parts.append(
                        f"- node={node.id} type={node.type} "
                        f"file={node.file_path} symbol={node.name}"
                    )
            for edge in graph.edges:
                if context_files is not None:
                    source_file = next(
                        (
                            node.file_path
                            for node in graph.nodes
                            if node.id == edge.source
                        ),
                        None,
                    )
                    target_file = next(
                        (
                            node.file_path
                            for node in graph.nodes
                            if node.id == edge.target
                        ),
                        None,
                    )
                    if source_file not in context_files and target_file not in context_files:
                        continue
                parts.append(
                    f"- edge={edge.type} source={edge.source} "
                    f"target={edge.target or '<unresolved>'} status={edge.status.value}"
                )
            if context_files is not None:
                parts.append(
                    "Planned source context: "
                    + ", ".join(sorted(context_files))
                )
        if index is not None and index.errors:
            parts.append(
                "Indexing limitations: "
                + "; ".join(f"{error.file_path}: {error.message}" for error in index.errors)
            )
        return "\n".join(part for part in parts if part)

    def _validate_location(self, project, index, graph, validator, location):
        from app.schemas.chat import ChatLocation

        hints = []
        if isinstance(location, ChatLocation):
            hints = list(location.relatednodes or [])
        elif isinstance(location, dict):
            hints = location.get("relatednodes", []) or []
            line = location.get("linenumber", location.get("line_number", location.get("line number")))
            location = {"filename": location.get("filename"), "linenumber": line, "relatednodes": hints}
            location = ChatLocation.model_validate(location)
            hints = list(location.relatednodes or [])
        else:
            location = ChatLocation.model_validate(location)
            hints = list(location.relatednodes or [])
        relative_path = location.filename
        project_root = self.workspace.project_root(project.project_id)
        resolved = (project_root / relative_path).resolve()
        if resolved != project_root and project_root not in resolved.parents:
            raise ValueError("Location is outside the project root.")
        if not resolved.exists() or not resolved.is_file():
            raise ValueError("Location file does not exist.")
        content = self.workspace.read_file(project.project_id, relative_path)
        lines = content.splitlines()
        if location.linenumber < 1 or location.linenumber > len(lines):
            raise ValueError("Location line number is invalid.")
        symbol_id = self._symbol_for_line(index, relative_path, location.linenumber)
        source = SourceReference(
            project_id=project.project_id,
            file_path=relative_path,
            module=next(
                (m.module for m in index.modules if m.file_path == relative_path),
                None,
            ),
            symbol=symbol_id or relative_path,
            line_start=location.linenumber,
            line_end=location.linenumber,
            file_hash=next(
                (m.file_hash for m in index.modules if m.file_path == relative_path),
                None,
            ),
        )
        item = EvidenceItem(
            evidence_id=f"evidence-{location.filename}:{location.linenumber}",
            evidence_type=EvidenceType.SOURCE_EXCERPT,
            description="Agent-proposed source location validated by the backend.",
            file_path=relative_path,
            source=source,
            excerpt=lines[location.linenumber - 1],
            symbol_id=symbol_id,
            file_hash=source.file_hash,
            observed=False,
        )
        item = validator.validate(item)
        if item.status.value == "valid":
            recorder = getattr(self, "_recorder", None)
            map_id = recorder.start("mapping", f"Mapping {relative_path}:{location.linenumber} to graph nodes") if recorder else None
            try:
                backend_matches = match_nodes_at_location(graph, relative_path, location.linenumber)
            except Exception as error:
                item.node_matches = []
                item.related_graph_nodes = [symbol_id] if symbol_id and symbol_id in validator.graph_node_ids else []
                msg = f"Graph node mapping failed for {relative_path}:{location.linenumber}: {error}"
                if hasattr(self, "_mapping_errors"):
                    self._mapping_errors.append(msg)
                if recorder and map_id:
                    recorder.finish(map_id, "failed", str(error)[:300])
                return item
            kept = []
            backend_ids = {m.node_id for m in backend_matches}
            for hint in hints:
                hid = hint.node_id if not isinstance(hint, dict) else hint.get("node_id")
                hfile = hint.file_path if not isinstance(hint, dict) else hint.get("file_path")
                if hid in validator.graph_node_ids and hfile == relative_path and hid not in backend_ids:
                    # Normalize hint to a match object
                    try:
                        from app.schemas.source_graph import SourceGraphNodeMatch as _M
                        kept.append(hint if not isinstance(hint, dict) else _M.model_validate(hint))
                    except Exception:
                        continue
            combined = list(backend_matches) + kept
            rank = {"route": 0, "method": 0, "function": 0, "class": 1, "module": 2}
            combined.sort(key=lambda m: (rank.get(m.node_type, 4), (m.end_line - m.start_line) if m.start_line is not None and m.end_line is not None else 10**9))
            seen, deduped = set(), []
            for m in combined:
                if m.node_id not in seen:
                    seen.add(m.node_id); deduped.append(m)
            item.node_matches = deduped
            related = []
            if symbol_id and symbol_id in validator.graph_node_ids:
                related.append(symbol_id)
            for m in deduped:
                if m.node_id not in related:
                    related.append(m.node_id)
            item.related_graph_nodes = related
            item = validator.validate(item)
            # validator may reset? preserve matches
            item.node_matches = deduped
            item.related_graph_nodes = related
            if recorder and map_id:
                recorder.finish(map_id, "ok", f"{len(deduped)} node(s) matched")
        else:
            item.related_graph_nodes = []
            item.node_matches = []
        return item

    @staticmethod
    def _symbol_for_line(index, file_path, line_number):
        candidates = [
            symbol
            for symbol in (*index.functions, *index.classes)
            if symbol.source.file_path == file_path
            and symbol.source.line_start is not None
            and symbol.source.line_end is not None
            and symbol.source.line_start <= line_number <= symbol.source.line_end
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda function: (
                (function.source.line_end or function.source.line_start)
                - (function.source.line_start or 0)
            ),
        ).id
