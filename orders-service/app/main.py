import os
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from .utils import publish_order_placed

app = FastAPI(
    title="Order-service",
    description=""
)