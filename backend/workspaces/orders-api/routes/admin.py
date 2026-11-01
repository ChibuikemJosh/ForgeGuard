from fastapi import APIRouter, Depends

from auth import get_current_customer
from db import CUSTOMERS
from models import Customer

router = APIRouter()


@router.get("/admin/customers")
def list_customers(customer: Customer = Depends(get_current_customer)) -> list[Customer]:
    return list(CUSTOMERS.values())
