from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class AnimeCreate(BaseModel):
    title: str
    start_date: Optional[date] = None
    total_episodes: Optional[int] = None
    source_id: Optional[str] = None


class AnimeOut(BaseModel):
    id: int
    title: str
    start_date: Optional[date]
    total_episodes: Optional[int]
    created_at: datetime
    source_id: Optional[str]


class EpisodeCreate(BaseModel):
    episode_code: str  # E01 / OVA1 / SP01
    episode_type: str  # main / ova / sp
    display_order: int
    title: Optional[str] = None
    air_date: Optional[date] = None


class EpisodeOut(BaseModel):
    episode_code: str
    episode_type: str
    display_order: int
    title: Optional[str]
    air_date: Optional[date]


class EpisodeReviewCreate(BaseModel):
    score: Optional[int] = Field(None, ge=0, le=10)
    comment: Optional[str] = None


class EpisodeReviewOut(BaseModel):
    score: Optional[int]
    comment: Optional[str]
    reviewed_at: datetime


class AnimeReviewCreate(BaseModel):
    score: Optional[int] = Field(None, ge=0, le=10)
    comment: Optional[str] = None


class AnimeReviewOut(BaseModel):
    score: Optional[int]
    comment: Optional[str]
    reviewed_at: datetime


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class CollectionAnimeCreate(BaseModel):
    anime_id: int


