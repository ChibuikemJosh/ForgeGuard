"""Derive candidate security rules from a project's own SourceGraph.

No rules are invented from thin air: every suggestion is anchored to an
observed route, parameter, or resource name in the indexed project.
"""
from __future__ import annotations

import re

from app.schemas.security import SecurityRule, Severity
from app.schemas.source_graph import SourceGraph

_PARAM_RE = re.compile(r"\{(\w+)(?::[^}]+)?\}")
_RESOURCE_RE = re.compile(r"(\w+)_id\b")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "resource"


def generate_rules(graph: SourceGraph) -> list[SecurityRule]:
    routes = [n for n in graph.nodes if n.type == "route"]
    rules: list[SecurityRule] = []
    seen: set[str] = set()

    def add(rule: SecurityRule) -> None:
        if rule.rule_id not in seen:
            seen.add(rule.rule_id)
            rules.append(rule)

    # Admin / privileged route groups.
    admin = [r for r in routes if "/admin" in (r.metadata.get("path") or r.name)]
    if admin:
        paths = sorted({str(r.metadata.get("path") or r.name) for r in admin})
        add(SecurityRule(
            rule_id="generated-admin-role-authorization",
            title="Admin routes in this project must verify the admin role",
            invariant="Every admin route in this project must verify the authenticated user has an admin/privileged role before returning data.",
            description=f"Derived from {len(admin)} admin route(s) found in this project: {', '.join(paths[:5])}.",
            severity=Severity.HIGH, category="authorization",
            indicators=[*paths[:5], "no role check"],
            concepts=["admin", "role", "authorization"],
        ))

    # Ownership: routes carrying a resource id parameter.
    resources: dict[str, list[str]] = {}
    for r in routes:
        path = str(r.metadata.get("path") or r.name)
        for param in _PARAM_RE.findall(path):
            m = _RESOURCE_RE.match(param)
            resource = m.group(1) if m else param.removesuffix("id").strip("_") or param
            resources.setdefault(resource, []).append(path)
    for resource, paths in sorted(resources.items()):
        if resource in {"id"}:
            continue
        add(SecurityRule(
            rule_id=f"generated-{_slug(resource)}-ownership-authorization",
            title=f"Users may access only their own {resource} resources",
            invariant=f"The authenticated user's identity must be compared with the owning user of the {resource} before {resource} data is returned.",
            description=f"Derived from route(s) with a {resource} identifier: {', '.join(sorted(set(paths))[:5])}.",
            severity=Severity.HIGH, category="authorization",
            indicators=[f"{resource} lookup by id", "missing owner comparison before return", *sorted(set(paths))[:3]],
            concepts=[resource, "ownership", "authorization"],
        ))

    # Authentication: any route surface at all implies an auth check rule.
    if routes and not admin:
        add(SecurityRule(
            rule_id="generated-authenticated-access",
            title="Routes in this project must require authentication",
            invariant="Every non-public route in this project must reject unauthenticated requests before returning data.",
            description=f"Derived from {len(routes)} route(s) found in this project.",
            severity=Severity.HIGH, category="authentication",
            indicators=["route handler", "no authentication dependency/check"],
            concepts=["authentication"],
        ))
    return rules[:8]
