from app.schemas.source_graph import SourceGraph, SourceGraphNode
from app.services.generated_rules import generate_rules


def _route(path, method="GET"):
    return SourceGraphNode(id=f"route:{path}", type="route", name=f"{method} {path}",
                           metadata={"http_method": method, "path": path, "handler": "h"})


def test_generated_rules_from_project_routes():
    graph = SourceGraph(project_id="p", nodes=[
        _route("/admin/users"), _route("/orders/{order_id}"), _route("/invoices/{invoice_id}")])
    ids = {r.rule_id for r in generate_rules(graph)}
    assert "generated-admin-role-authorization" in ids
    assert "generated-order-ownership-authorization" in ids
    assert "generated-invoice-ownership-authorization" in ids


def test_generated_rules_empty_without_routes():
    graph = SourceGraph(project_id="p", nodes=[])
    assert generate_rules(graph) == []
