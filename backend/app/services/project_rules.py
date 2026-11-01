"""Preset security rules for project investigation."""
from app.schemas.security import SecurityRule, Severity
from app.services.security_analysis import ORDER_OWNERSHIP_RULE

RULE_PRESETS: list[SecurityRule] = [
    ORDER_OWNERSHIP_RULE.model_copy(update={
        "description": "An authenticated customer must only retrieve orders they own.",
        "severity": Severity.HIGH,
        "indicators": ["order lookup by id", "missing owner comparison before return"],
    }),
    SecurityRule(
        rule_id="admin-role-authorization",
        title="Admin-only endpoints must verify the admin role",
        invariant="Endpoints under /admin must verify the authenticated user has the admin role before returning data.",
        description="Admin endpoints must check role, not only authentication.",
        severity=Severity.HIGH,
        indicators=["/admin route", "no role check", "returns all customers"],
    ),
    SecurityRule(
        rule_id="invoice-ownership-authorization",
        title="Customers may access only their own invoices",
        invariant="The authenticated customer ID must be compared with the invoice customer_id before invoice data is returned.",
        description="Invoice list and detail endpoints must be scoped to the authenticated customer.",
        severity=Severity.HIGH,
        indicators=["invoice lookup", "wrong ownership field comparison", "unscoped invoice list"],
    ),
]
