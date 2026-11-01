def get_order_for_customer(order_id: str, customer_id: str):
    from repositories.order_repository import find_order
    order = find_order(order_id)
    # VULNERABILITY: no ownership check before returning
    return order
