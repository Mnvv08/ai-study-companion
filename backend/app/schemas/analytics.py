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


class RecommendationItem(BaseModel):
    topic: str = Field(..., description="The recommended topic to revise")
    reason: str = Field(..., description="Reason for the recommendation based on performance")
    document_id: str = Field(..., description="ID of the document this topic is associated with")
    document_filename: str = Field(..., description="Filename of the associated document")


class RecommendationsResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(..., description="List of revision recommendations for the top 3 weakest topics")

