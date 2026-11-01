from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/orders/{order_id}")
def get_order(order_id: str, customer_id: str):
    from services.order_service import get_order_for_customer
    return get_order_for_customer(order_id, customer_id)
