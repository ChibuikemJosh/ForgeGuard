# Orders API (sample)

Intentionally vulnerable sample code for local Forge Guard testing. Do not deploy.

Planted issues (for the human tester; this file is not sent to the model):

1. `routes/orders.py` — `GET /orders/{order_id}` authenticates but returns any order without an owner check.
2. `routes/admin.py` — `GET /admin/customers` returns all customers with no admin role check.
3. `routes/invoices.py` — `GET /invoices` ownership check compares the wrong field and the list handler returns data before a correct check.

Safe control: `routes/profile.py` correctly checks ownership and should not be flagged.

Reset after applying fixes: `git checkout backend/workspaces/orders-api`
