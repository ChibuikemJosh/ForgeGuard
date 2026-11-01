from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_customer
from db import INVOICES
from models import Customer, Invoice

router = APIRouter()


@router.get("/invoices")
def list_invoices(customer: Customer = Depends(get_current_customer)) -> list[Invoice]:
    invoices = list(INVOICES.values())
    return invoices


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, customer: Customer = Depends(get_current_customer)) -> Invoice:
    invoice = INVOICES.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.invoice_id != customer.customer_id:
        raise HTTPException(status_code=403, detail="Invoice does not belong to customer.")
    return invoice
