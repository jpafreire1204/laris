"""
Laris - Podcast Models
Modelos para coleções e episódios de podcast.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


def slugify(text: str) -> str:
    """Converte texto para slug URL-safe."""
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


class Collection(BaseModel):
    """Uma coleção de episódios (como uma playlist)."""
    id: str
    name: str
    slug: str
    description: str = ""
    author: str = "Laris"
    email: str = "contato@laris.com.br"
    image_url: Optional[str] = None
    language: str = "pt-BR"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Episode(BaseModel):
    """Um episódio de podcast."""
    id: str
    collection_id: str
    title: str
    description: str = ""
    audio_url: str
    audio_size: int = 0  # bytes
    duration_seconds: int = 0
    guid: str  # identificador único estável
    pub_date: datetime = Field(default_factory=datetime.utcnow)
    image_url: Optional[str] = None
    explicit: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateCollectionRequest(BaseModel):
    """Request para criar coleção."""
    name: str
    description: str = ""
    author: str = "Laris"
    email: str = "contato@laris.com.br"


class CreateEpisodeRequest(BaseModel):
    """Request para criar episódio."""
    collection_id: str
    title: str
    description: str = ""
    job_id: str  # ID do job de áudio gerado


class CollectionResponse(BaseModel):
    """Response com dados da coleção."""
    id: str
    name: str
    slug: str
    description: str
    feed_url: str
    episode_count: int
    created_at: datetime


class EpisodeResponse(BaseModel):
    """Response com dados do episódio."""
    id: str
    title: str
    description: str
    audio_url: str
    duration_seconds: int
    pub_date: datetime
    collection_name: str
