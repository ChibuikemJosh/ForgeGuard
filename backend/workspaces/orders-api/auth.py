from fastapi import Header, HTTPException

from db import CUSTOMERS
from models import Customer


def get_current_customer(x_customer_id: str = Header(default="")) -> Customer:
    customer = CUSTOMERS.get(x_customer_id)
    if customer is None:
        raise HTTPException(status_code=401, detail="Unknown customer.")
    return customer


def get_current_user_role(customer: Customer) -> str:
    return customer.role
