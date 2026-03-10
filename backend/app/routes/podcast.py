"""
Laris - Podcast Routes
Endpoints para gerenciar coleções, episódios e feeds RSS.
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, FileResponse, JSONResponse
from typing import List

from app.models.podcast import (
    CreateCollectionRequest,
    CreateEpisodeRequest,
    CollectionResponse,
    EpisodeResponse
)
from app.services.podcast_service import (
    create_collection,
    get_all_collections,
    get_collection,
    get_collection_by_slug,
    get_episodes_by_collection,
    create_episode,
    get_feed_path,
    get_episode_audio_path,
    regenerate_feed
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_base_url(request: Request) -> str:
    """Obtém a URL base do servidor."""
    # Em produção, usar HTTPS
    scheme = request.headers.get('x-forwarded-proto', request.url.scheme)
    host = request.headers.get('x-forwarded-host', request.url.netloc)
    return f"{scheme}://{host}"


@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(request: Request):
    """Lista todas as coleções."""
    collections = get_all_collections()
    base_url = get_base_url(request)

    return [
        CollectionResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            feed_url=f"{base_url}/api/podcast/{c.slug}/feed.xml",
            episode_count=len(get_episodes_by_collection(c.id)),
            created_at=c.created_at
        )
        for c in collections
    ]


@router.post("/collections", response_model=CollectionResponse)
async def create_new_collection(request: Request, data: CreateCollectionRequest):
    """Cria uma nova coleção."""
    collection = create_collection(
        name=data.name,
        description=data.description,
        author=data.author,
        email=data.email
    )

    base_url = get_base_url(request)

    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        feed_url=f"{base_url}/api/podcast/{collection.slug}/feed.xml",
        episode_count=0,
        created_at=collection.created_at
    )


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection_detail(collection_id: str, request: Request):
    """Obtém detalhes de uma coleção."""
    collection = get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Coleção não encontrada")

    base_url = get_base_url(request)

    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        feed_url=f"{base_url}/api/podcast/{collection.slug}/feed.xml",
        episode_count=len(get_episodes_by_collection(collection.id)),
        created_at=collection.created_at
    )


@router.get("/collections/{collection_id}/episodes", response_model=List[EpisodeResponse])
async def list_collection_episodes(collection_id: str):
    """Lista episódios de uma coleção."""
    collection = get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Coleção não encontrada")

    episodes = get_episodes_by_collection(collection_id)

    return [
        EpisodeResponse(
            id=e.id,
            title=e.title,
            description=e.description,
            audio_url=e.audio_url,
            duration_seconds=e.duration_seconds,
            pub_date=e.pub_date,
            collection_name=collection.name
        )
        for e in episodes
    ]


@router.post("/episodes")
async def create_new_episode(request: Request, data: CreateEpisodeRequest):
    """Cria um novo episódio a partir de um job de áudio."""
    base_url = get_base_url(request)

    episode, error = create_episode(
        collection_id=data.collection_id,
        title=data.title,
        job_id=data.job_id,
        base_url=base_url,
        description=data.description
    )

    if error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": error}
        )

    collection = get_collection(data.collection_id)

    return {
        "success": True,
        "episode": {
            "id": episode.id,
            "title": episode.title,
            "audio_url": episode.audio_url,
            "guid": episode.guid
        },
        "feed_url": f"{base_url}/api/podcast/{collection.slug}/feed.xml"
    }


@router.get("/{slug}/feed.xml")
async def get_feed(slug: str, request: Request):
    """Retorna o feed RSS de uma coleção."""
    collection = get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Coleção não encontrada")

    # Regenera feed para garantir que está atualizado
    base_url = get_base_url(request)
    regenerate_feed(slug, base_url)

    feed_path = get_feed_path(slug)
    if not feed_path:
        raise HTTPException(status_code=404, detail="Feed não encontrado")

    with open(feed_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/rss+xml; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{slug}-feed.xml"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/{slug}/episodes/{job_id}/audio.mp3")
async def get_episode_audio(slug: str, job_id: str):
    """Retorna o áudio de um episódio."""
    audio_path = get_episode_audio_path(slug, job_id)

    if not audio_path:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{job_id}.mp3",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=31536000"  # 1 ano de cache
        }
    )
