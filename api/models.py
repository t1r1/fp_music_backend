from pydantic import BaseModel
from typing import Optional


class Mood(BaseModel):
    id: int
    mood: str
    annotation: str


class ListMoodsResponse(BaseModel):
    moods: list[Mood]


class Track(BaseModel):
    id: int
    title: str
    artist: str
    genre: str
    filepath: str
    relevance: float


class RecommendationsResponse(BaseModel):
    mood_id: int
    tracks: list[Track]


class EvaluationResponse(BaseModel):
    recommendation_id: int
    liked: Optional[int]


class EvaluationRequest(BaseModel):
    recommendation_id: int
    liked: int  # must be 1 or -1
