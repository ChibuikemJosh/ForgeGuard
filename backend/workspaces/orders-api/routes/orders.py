from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_customer
from db import ORDERS
from models import Customer, Order

router = APIRouter()


@router.get("/orders/{order_id}")
def get_order(order_id: str, customer: Customer = Depends(get_current_customer)) -> Order:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order
