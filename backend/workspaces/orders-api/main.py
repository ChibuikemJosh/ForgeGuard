from fastapi import FastAPI

from routes import admin, invoices, orders, profile

app = FastAPI(title="Orders API")
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(invoices.router)
app.include_router(profile.router)
