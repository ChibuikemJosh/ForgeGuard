from models import Customer, Invoice, Order

CUSTOMERS: dict[str, Customer] = {
    "alice": Customer("alice", "Alice", "alice@example.com", "customer"),
    "bob": Customer("bob", "Bob", "bob@example.com", "customer"),
    "root": Customer("root", "Root", "root@example.com", "admin"),
}

ORDERS: dict[str, Order] = {
    "order-alice": Order("order-alice", "alice", "Keyboard", 9900),
    "order-bob": Order("order-bob", "bob", "Monitor", 24900),
}

INVOICES: dict[str, Invoice] = {
    "inv-alice": Invoice("inv-alice", "alice", "order-alice", 9900),
    "inv-bob": Invoice("inv-bob", "bob", "order-bob", 24900),
}
