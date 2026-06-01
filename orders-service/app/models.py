from sqlalchemy import Column, Integer, String
from .database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String, nullable = False)
    product_id = Column(Integer, nullable = False)
    product_name = Column(String, nullable = False)
    quantity = Column(Integer, nullable = False)

    