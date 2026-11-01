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
from app.services.project_workspace import ProjectReference, WorkspaceService
# Ram's agent is imported lazily so this module can be imported without the
# optional LangChain dependency unless an investigation actually runs.


class SecurityInvestigationService:
    def __init__(self, workspace, agent=None):
        self.workspace = workspace
        self.agent = agent

    def investigate(self, project, index, graph, rule, agent=None, session_id=None):
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
                    follow_up=True,
                )
        except AgentConfigurationError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="Investigation could not run because the AI provider is not configured.",
                truncated=getattr(agent, "last_truncated", False),
            )
        except ProjectFolderError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                truncated=getattr(agent, "last_truncated", False),
            )
        except AgentResponseError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="The agent response could not be parsed into locations.",
                truncated=getattr(agent, "last_truncated", False),
            )
        except Exception as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[f"Investigation failed: {error}"],
                truncated=getattr(agent, "last_truncated", False),
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
        for location in locations:
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
    ):
        parameters = inspect.signature(agent.find_violations).parameters
        kwargs = {}
        if "context_files" in parameters:
            kwargs["context_files"] = context_files
        if "follow_up" in parameters:
            kwargs["follow_up"] = follow_up
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

        if not isinstance(location, ChatLocation):
            if isinstance(location, dict):
                line = location.get("linenumber", location.get("line_number", location.get("line number")))
                location = {"filename": location.get("filename"), "linenumber": line}
            location = ChatLocation.model_validate(location)
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
        if item.status.value == "valid" and symbol_id is not None:
            item.related_graph_nodes = (
                [symbol_id] if symbol_id in validator.graph_node_ids else []
            )
            item = validator.validate(item)
        else:
            item.related_graph_nodes = []
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
