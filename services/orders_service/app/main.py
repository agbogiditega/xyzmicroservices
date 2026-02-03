from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .domain import create_order
from .publisher import publish_order_created

app = FastAPI(title="orders-service")

class CreateOrderRequest(BaseModel):
    sku: str
    qty: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders", status_code=201)
def post_orders(req: CreateOrderRequest):
    try:
        order = create_order(req.sku, req.qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    publish_order_created({"order_id": order.order_id, "sku": order.sku, "qty": order.qty})
    return {"order_id": order.order_id}
