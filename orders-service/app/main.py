import os
import httpx
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from .utils import publish_order_placed
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Order
from .utils import publish_order_placed

# creating the database tables if not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order-service",
    description="Orchestrates microservice orders and broadcasts async inventory events via RabbitMQ"
)

# Read the internal microservice URLS from envronment variables
USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://flask_users_service:5001"
)
PRODUCTS_SERVICE_URL = os.getenv(
    "PRODUCTS_SERVICE_URL",
    "http://fastapi_products_service:5002"
)

# Request validtaion schemas
class OrderCreate(BaseModel):
    user_id:int
    product_id: int
    quantity: int

    class Config:
        json_schema_extra = {
            "example":{
                "user_id":1,
                "product_id":5,
                "quantity": 2
            }
        }

# creating Endpoints
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "orders-service"}

"""
    Creates a new order purchase flow.
    1. Verifies the user exists via the User Service.
    2. Broadcasts a non blocking background inventory reduction message to RabbitMQ.
"""
@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order:OrderCreate, db: Session = Depends(get_db)):
    username = "UnKnown"
    product_name= "Unknown"

    #1. Validate user existence
    async with httpx.AsyncClient() as client:
        try:
            # Get user_id from Flask user service GET endpoint: /users/<id>
            user_response = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}", timeout=3)

            if user_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Order rejected: User ID {order.user_id} does not exist"
                )
            elif user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail = "Failed to communicate realiably with User verification service"
                )
            
            # Extract username from the response body
            user_data = user_response.json()
            username = user_data.get("username", "Unknown User")
        
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"User verification service is temporarrily unreachable: {exc}"
            )
        
    # 2. Validate product exixtance
        try:
            # Pointing to your product retrieval endpoint 
            product_response = await client.get(f"{PRODUCTS_SERVICE_URL}/products/{order.product_id}", timeout=3)

            if product_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Order rejected: Product ID {order.product_id} does not exist"
                )
            elif product_response.status_code !=200:
                raise HTTPException(
                    status_code = status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to communicate reliably with Product verification service"
                )
            # extract product name from the response body
            product_data = product_response.json()
            product_name = product_data.get("name", "Unknown Product")
            available_stock = product_data.get("stock",0)

            # Reject order if stock < quantity request by user
            if available_stock < order.quantity:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = f"Order Rejected: Insufficient stock. Requested {order.quantity}, but only {available_stock} available. "
                )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Product verification service is temporarily unreachable: {exc}"
            )
    
    # Save to DB and trigger background inventory reduction event
    db_order = Order(
        user_id = order.user_id,
        username = username,
        product_id = order.product_id,
        product_name = product_name,
        quantity = order.quantity
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
                
    # 2. Trigger Asynchoronous inventory Allocation
    try:
        publish_order_placed(product_id=order.product_id, quantity=order.quantity)
    except Exception as mq_err:
        # If the broker is atructurally unreachable throw a 500 so client know the transaction failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order accepted but critical background worker event broadcast faild: {mq_err}" 
        )
    
    # save to DB 
    return{
        "message": "Order processed and saved successfully",
        "order_details": {
            "order_id": db_order.id,  # Clean numerical sequence!
            "user_id": db_order.user_id,
            "username": db_order.username,
            "product_id": db_order.product_id,
            "product_name": db_order.product_name,
            "quantity": db_order.quantity
        }
    }

# Get all orders
@app.get("/orders", status_code=status.HTTP_200_OK)
async def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [
        {
            "order_id": o.id,
            "user_id": o.user_id,
            "username": o.username,
            "product_id": o.product_id,
            "product_name": o.product_name,
            "quantity": o.quantity
        }
        for o in orders
    ]

# Get order by ID
@app.get("/orders/{order_id}", status_code=status.HTTP_200_OK)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {order_id} cannot be found"
        )
    return {
        "order_id": order.id,
        "user_id": order.user_id,
        "username": order.username,
        "product_id": order.product_id,
        "product_name": order.product_name,
        "quantity": order.quantity
    }

class OrderUpdate(BaseModel):
    new_quantity: int

# update an existing order's quantity
@app.put("/orders/{order_id}", status_code=status.HTTP_200_OK)
async def update_order(order_id: int, order_update: OrderUpdate, db: Session = Depends(get_db)):
    # Look up existing order in the database
    existing_order = db.query(Order).filter(Order.id == order_id).first()

    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {order_id} cannot be found"
        )
    
    if order_update.new_quantity <=0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero"
        )
    # Calculate quantity difference for RabbitMQ update
    quantity_diff = order_update.new_quantity - existing_order.quantity

    # Update the order quantity in the database
    existing_order.quantity = order_update.new_quantity
    db.commit()
    db.refresh(existing_order)



    # Trigger Asynchronous inventory update with the quantity difference
    try:
        if quantity_diff != 0:  # Only publish if there is a change in quantity
            publish_order_placed(product_id=existing_order.product_id, quantity=quantity_diff)
    except Exception as mq_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order updated but critical background worker event broadcast faild: {mq_err}" 
        ) 

    return {
        "message": f"Order ID {order_id} has been updated successfully",
        "order_details": {
            "order_id": existing_order.id,
            "user_id": existing_order.user_id,
            "username": existing_order.username,
            "product_id": existing_order.product_id,
            "product_name": existing_order.product_name,
            "quantity": existing_order.quantity
        }
        
    }


# delete an existing order
@app.delete("/orders/{order_id}", status_code = status.HTTP_200_OK)
async def delete_order(order_id: int, db: Session =Depends(get_db)):
    # Look up existing order in the database
    existing_order = db.query(Order).filter(Order.id == order_id).first()

    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID - {order_id} cannot be found"
        )
    
    # Calculate negative quantity for restore over RabbitMQ
    try:
        restore_quantity = -existing_order.quantity
        publish_order_placed(product_id=existing_order.product_id, quantity=restore_quantity)
    except Exception as mq_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order deletion failed: {mq_err}"
        ) 
    
    # Delete the order from the database
    db.delete(existing_order)   
    db.commit()

    return {
        "message": f"Order ID {order_id} has been deleted and inventory restored successfully",
        "order_details": {
            "order_id": existing_order.id,
            "user_id": existing_order.user_id,
            "username": existing_order.username,
            "product_id": existing_order.product_id,
            "product_name": existing_order.product_name,
            "quantity": existing_order.quantity
        }
        
    }
