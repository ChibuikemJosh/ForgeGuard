from dataclasses import dataclass


@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    role: str = "customer"


@dataclass
class Order:
    order_id: str
    owner_id: str
    item: str
    total_cents: int


@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    order_id: str
    amount_cents: int
