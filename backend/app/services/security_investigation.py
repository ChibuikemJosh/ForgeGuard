# test
from __future__ import annotations

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
        try:
            locations = agent.find_violations(
                self._rule_text(rule),
                project_folder,
                investigation_id,
            )
        except AgentConfigurationError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="Investigation could not run because the AI provider is not configured.",
            )
        except ProjectFolderError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
            )
        except AgentResponseError as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[str(error)],
                summary="The agent response could not be parsed into locations.",
            )
        except Exception as error:
            return InvestigationResult(
                investigation_id=investigation_id,
                project_id=project.project_id,
                rule_id=rule.rule_id,
                status=InvestigationStatus.FAILED,
                errors=[f"Investigation failed: {error}"],
            )

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
                    title=f"Potential violation of {rule.title}",
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
        return InvestigationResult(
            investigation_id=investigation_id,
            project_id=project.project_id,
            rule_id=rule.rule_id,
            status=status,
            findings=findings,
            errors=errors,
            summary=(
                f"Investigated {len(index.files)} files; agent returned "
                f"{len(locations)} location(s), {len(valid_items)} validated."
            ),
        )

    def _rule_text(self, rule):
        parts = [rule.title, rule.invariant]
        if rule.description:
            parts.append(rule.description)
        if rule.expected_property:
            parts.append(f"Expected property: {rule.expected_property}")
        if rule.guidance:
            parts.append(f"Guidance: {rule.guidance}")
        return "\n".join(part for part in parts if part)

    def _validate_location(self, project, index, graph, validator, location):
        from app.schemas.chat import ChatLocation

        if not isinstance(location, ChatLocation):
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
        else:
            item.related_graph_nodes = []
        return item

    @staticmethod
    def _symbol_for_line(index, file_path, line_number):
        candidates = [
            function
            for function in index.functions
            if function.source.file_path == file_path
            and function.source.line_start is not None
            and function.source.line_end is not None
            and function.source.line_start <= line_number <= function.source.line_end
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
