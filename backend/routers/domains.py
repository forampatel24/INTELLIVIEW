"""Domain listing endpoints (phase 15)."""

from typing import Optional

from fastapi import APIRouter, Depends

from ai.domains import DomainService
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("/categories")
def list_categories(user: dict = Depends(get_current_user)):
    return DomainService().list_categories()


@router.get("")
def list_domains(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    return DomainService().list_domains(category=category)