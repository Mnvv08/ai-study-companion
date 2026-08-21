"""
app/schemas/analytics.py
────────────────────────
Pydantic schemas for analytics endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


class WeakTopicItem(BaseModel):
    topic: str = Field(..., description="The name of the topic category")
    total_attempted: int = Field(..., description="Total number of questions answered in this topic")
    correct_count: int = Field(..., description="Number of questions answered correctly")
    accuracy_percentage: float = Field(..., description="Accuracy percentage (0.0 to 100.0)")


class WeakTopicsResponse(BaseModel):
    weak_topics: List[WeakTopicItem] = Field(..., description="List of weak topics sorted from lowest to highest accuracy")
