"""
app/schemas/user.py
───────────────────
Pydantic schemas for User settings operations.
"""

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    persona_mode: bool = Field(..., description="Enable or disable Hinglish student-mentor persona mode")


class UserSettingsResponse(BaseModel):
    persona_mode: bool = Field(..., description="Whether Hinglish student-mentor persona mode is active")

    class Config:
        from_attributes = True
