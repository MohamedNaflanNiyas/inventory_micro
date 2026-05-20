from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.future import select
from pydantic import BaseModel
from .config import DATABASE_URL
import asyncio
from sqlalchemy.exc import OperationalError

app = FastAPI(title="Products Service")

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

class ProductCreate(BaseModel):
    name: str

class ProductResponse(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# Database dependency Injection
async def get_db():
    async with async_session() as session:
        yield session

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
    new_product = ProductDB(name= product.name)
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


@app.put("/products/{product_id}/stock", status_code=200)
async def deduct_stock(product_id: int, quantity: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductDB).where(ProductDB.id == product_id))
    product = result.scalar().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    product.stock -= quantity
    await db.commit()
    return product