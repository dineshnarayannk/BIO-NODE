from fastapi import APIRouter
from .routes import health_router, compounds_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(compounds_router)
