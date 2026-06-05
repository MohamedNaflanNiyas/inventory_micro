# This is the main application file for the Products Service. It defines the FastAPI application,
# sets up the database connection using SQLAlchemy, and implements the API endpoints for managing products. 
# The service allows you to create new products, retrieve product information, update stock levels, and delete products. 
# It also includes error handling for various scenarios such as insufficient stock or product not found.

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.future import select
from pydantic import BaseModel
from .config import DATABASE_URL
import asyncio
import os
from sqlalchemy.exc import OperationalError

app = FastAPI(title="Products Service")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@postgres_db:5432/products_db"
)

# set up DB Engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# SQLAlchemy DB model
class ProductDB(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    stock = Column(Integer, default=10)

# Request validation schemas
class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int

# Response model
class ProductResponse(BaseModel):
    id: int
    name: str
    price:float
    stock:int
    class Config:
        from_attributes = True


# Schema for stock update
class StockUpdate(BaseModel):
    quantity: int

# Database dependency Injection
async def get_db():
    async with async_session() as session:
        yield session

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup():
    retries = 5
    while retries >0:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Succesfully connected to DB")
            break
        except (OperationalError, OSError):
            retries -= 1
            print(f"DB not ready yet. Retrying in 5 seconds....({retries})")
            await asyncio.sleep(5)
    
    if retries == 0:
        raise Exception("Unable to connect to DB")


# Add new products
@app.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate, db: AsyncSession=Depends(get_db)):
    new_product = ProductDB(
        name= product.name,
        price=product.price,
        stock=product.stock
        )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product

# Get all products
@app.get("/products", response_model=list[ProductResponse])
async def get_products(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select
    result = await db.execute(select(ProductDB))
    return result.scalars().all()

# get products by id
@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(ProductDB, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Update product stock after order is placed
@app.put("/products/deduct-stock/{product_id}", status_code=200)
async def deduct_stock(
    product_id: int, 
    payload: StockUpdate,
    db: AsyncSession = Depends(get_db) 
):
    result = await db.execute(
        select(ProductDB).where(ProductDB.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    if product.stock < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    product.stock -= payload.quantity
    await db.commit()
    return {
        "message": "Stock deducted successfully",
        "product": {
            "id": product.id,
            "name": product.name,
            "stock": product.stock
        }
    }

# Update product stock  - New Product stock 
@app.put("/products/add-stock/{product_id}", status_code=200)
async def add_stock(
    product_id: int,
    payload: StockUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProductDB).where(ProductDB.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code = 400, detail="Product not found")
    
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    
    product.stock += payload.quantity
    await db.commit()
    
    return {
        "message": "Stock updated successfully",
        "product_id": product.id,
        "product_name": product.name,
        "old_stock": product.stock - payload.quantity,
        "new_stock": product.stock
    }

# Delete product by ID
@app.delete("/products/{product_id}", status_code=200)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductDB).where(ProductDB.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()

    return {
        "message": f"Product {product_id} deleted successfully"
    }