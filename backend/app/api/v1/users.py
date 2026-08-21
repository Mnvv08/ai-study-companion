"""
app/api/v1/users.py
───────────────────
API router for User Profile and settings management.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import UserSettingsUpdate, UserSettingsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/settings", response_model=UserSettingsResponse)
def get_user_settings(
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current user's settings (e.g. persona_mode)."""
    return current_user


@router.patch("/me/settings", response_model=UserSettingsResponse)
def update_user_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the current user's settings (e.g. persona_mode)."""
    current_user.persona_mode = payload.persona_mode
    db.commit()
    db.refresh(current_user)
    return current_user
