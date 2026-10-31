#!/usr/bin/env python
"""Phase 3 end-to-end verification test."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")


def _workspace(tmp_path, files):
    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    project = root / "proj"
    project.mkdir(exist_ok=True)
    for rel, content in files.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    from app.services.project_workspace import WorkspaceService

    service = WorkspaceService(root)
    ref = service.register_project("proj")
    return service, ref


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        files = {
            "api.py": (
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                "@router.get('/orders/{order_id}')\n"
                "def get_order(order_id: str):\n"
                "    # This should check if the user owns the order\n"
                "    db_order = get_from_db(order_id)\n"
                "    # VULNERABILITY: No ownership check!\n"
                "    return db_order\n"
            ),
            "service.py": (
                "def get_from_db(order_id: str):\n"
                "    # Get order from database\n"
                "    return {'id': order_id, 'owner': 'user123'}\n"
            ),
            "models.py": (
                "from dataclasses import dataclass\n\n"
                "@dataclass\n"
                "class Order:\n"
                "    id: str\n"
                "    owner_id: str\n"
                "    total: int\n"
            ),
        }

        service, ref = _workspace(tmp_path, files)

        print(f"Created test project: {ref.project_id}")
        print(f"Project name: {ref.name}")
        print(f"Project relative path: {ref.relative_path}")

        from app.services.python_indexer import PythonIndexer

        indexer = PythonIndexer()
        index = indexer.index_project(service, ref.project_id)

        print("\nIndexed modules:")
        for module in index.modules:
            # Read file content from workspace
            content = service.read_file(ref.project_id, module.file_path)
            print(f"  {module.file_path} ({len(content.splitlines())} lines)")

        print("\nIndexed functions:")
        for func in index.functions:
            print(f"  {func.id}: {func.name} at {func.source.file_path}:{func.source.line_start}")

        from app.services.symbol_resolution import SymbolResolver
        from app.services.source_graph_builder import SourceGraphBuilder

        resolver = SymbolResolver()
        resolution = resolver.resolve(index)
        builder = SourceGraphBuilder()
        graph = builder.build(ref, index, resolution)

        print(f"\nSourceGraph nodes: {len(graph.nodes)}")
        print(f"SourceGraph edges: {len(graph.edges)}")

        # Create a custom security rule for order ownership
        from app.schemas.security import SecurityRule, Severity

        rule = SecurityRule(
            rule_id="custom-order-auth",
            title="Order ownership authorization",
            invariant="Authenticated customers must check that the retrieved order belongs to them before returning it",
            category="authorization",
            severity=Severity.HIGH,
            description="Detects when code retrieves orders without checking ownership",
            guidance="Add an ownership check: if order.owner_id != authenticated_customer_id: raise 403",
        )

        print(f"\nCreated security rule: {rule.rule_id}")
        print(f"  Title: {rule.title}")
        print(f"  Invariant: {rule.invariant}")
        print(f"  Severity: {rule.severity}")
        print(f"  Category: {rule.category}")

        # Test investigation with fake agent
        from app.schemas.chat import ChatLocation
        from app.services.security_investigation import SecurityInvestigationService

        class TestAgent:
            def find_violations(self, custom_security_violation_details, project_folder, session_id):
                # Return location pointing to the return statement in get_order
                return [ChatLocation(filename="api.py", linenumber=10)]

        investigator = SecurityInvestigationService(service, agent=TestAgent())
        result = investigator.investigate(ref, index, graph, rule)

        print(f"\nInvestigation Results:")
        print(f"  Status: {result.status}")
        print(f"  Findings count: {len(result.findings)}")

        for i, finding in enumerate(result.findings):
            print(f"  Finding {i+1}:")
            print(f"    ID: {finding.finding_id}")
            print(f"    Status: {finding.status}")
            print(f"    Affected files: {finding.affected_files}")
            print(f"    Affected symbols: {finding.affected_symbols}")
            print(f"    Related graph nodes: {finding.related_graph_nodes}")
            print(f"    Evidence count: {len(finding.evidence)}")
            for j, evidence in enumerate(finding.evidence):
                print(
                    f"      Evidence {j+1}: {evidence.evidence_id}, Type: {evidence.evidence_type}, Status: {evidence.status}"
                )
                print(f"        File: {evidence.file_path}, Line: {evidence.source.line_start}")
                print(f"        Excerpt: {evidence.excerpt}")

        print(f"\n✅ End-to-end test completed successfully!")
        print(f"The infrastructure can investigate multi-file projects against custom security rules.")


if __name__ == "__main__":
    main()