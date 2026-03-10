"""
Laris - Podcast Service
Gerencia coleções e episódios, gera feeds RSS compatíveis com Spotify.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

from app.models.podcast import Collection, Episode, slugify
from app.utils.file_utils import OUTPUTS_DIR, ensure_outputs_dir

logger = logging.getLogger(__name__)

# Diretório para dados de podcast
PODCAST_DIR = OUTPUTS_DIR / "podcast"
COLLECTIONS_FILE = PODCAST_DIR / "collections.json"
EPISODES_FILE = PODCAST_DIR / "episodes.json"


def ensure_podcast_dir():
    """Garante que o diretório de podcast existe."""
    ensure_outputs_dir()
    PODCAST_DIR.mkdir(exist_ok=True)


def load_collections() -> List[Collection]:
    """Carrega todas as coleções."""
    ensure_podcast_dir()
    if not COLLECTIONS_FILE.exists():
        return []
    try:
        with open(COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Collection(**c) for c in data]
    except Exception as e:
        logger.error(f"Erro ao carregar coleções: {e}")
        return []


def save_collections(collections: List[Collection]):
    """Salva todas as coleções."""
    ensure_podcast_dir()
    with open(COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump([c.model_dump(mode='json') for c in collections], f, indent=2, default=str)


def load_episodes() -> List[Episode]:
    """Carrega todos os episódios."""
    ensure_podcast_dir()
    if not EPISODES_FILE.exists():
        return []
    try:
        with open(EPISODES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Episode(**e) for e in data]
    except Exception as e:
        logger.error(f"Erro ao carregar episódios: {e}")
        return []


def save_episodes(episodes: List[Episode]):
    """Salva todos os episódios."""
    ensure_podcast_dir()
    with open(EPISODES_FILE, 'w', encoding='utf-8') as f:
        json.dump([e.model_dump(mode='json') for e in episodes], f, indent=2, default=str)


def create_collection(name: str, description: str = "", author: str = "Laris", email: str = "contato@laris.com.br") -> Collection:
    """Cria uma nova coleção."""
    collections = load_collections()

    # Gera slug único
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    existing_slugs = {c.slug for c in collections}
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    collection = Collection(
        id=str(uuid.uuid4())[:8],
        name=name,
        slug=slug,
        description=description,
        author=author,
        email=email
    )

    collections.append(collection)
    save_collections(collections)

    logger.info(f"Coleção criada: {name} ({slug})")
    return collection


def get_collection(collection_id: str) -> Optional[Collection]:
    """Busca uma coleção por ID."""
    collections = load_collections()
    for c in collections:
        if c.id == collection_id:
            return c
    return None


def get_collection_by_slug(slug: str) -> Optional[Collection]:
    """Busca uma coleção por slug."""
    collections = load_collections()
    for c in collections:
        if c.slug == slug:
            return c
    return None


def get_all_collections() -> List[Collection]:
    """Retorna todas as coleções."""
    return load_collections()


def get_episodes_by_collection(collection_id: str) -> List[Episode]:
    """Retorna episódios de uma coleção."""
    episodes = load_episodes()
    return [e for e in episodes if e.collection_id == collection_id]


def get_audio_duration(audio_path: Path) -> int:
    """Obtém duração do áudio em segundos."""
    try:
        # Tenta usar mutagen para duração precisa
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_path))
        return int(audio.info.length)
    except ImportError:
        # Fallback: estima baseado no tamanho (128kbps)
        size = audio_path.stat().st_size
        return int(size / (128 * 1024 / 8))  # bytes / (kbps * 1024 / 8)
    except Exception:
        return 0


def create_episode(
    collection_id: str,
    title: str,
    job_id: str,
    base_url: str,
    description: str = ""
) -> Tuple[Optional[Episode], Optional[str]]:
    """
    Cria um novo episódio a partir de um job de áudio.

    Args:
        collection_id: ID da coleção
        title: Título do episódio
        job_id: ID do job que gerou o áudio
        base_url: URL base do servidor (ex: https://laris.com.br)
        description: Descrição opcional

    Returns:
        Tupla (episódio, erro)
    """
    # Verifica coleção
    collection = get_collection(collection_id)
    if not collection:
        return None, "Coleção não encontrada"

    # Busca o arquivo de áudio
    ensure_outputs_dir()
    audio_path = None
    for suffix in ["_final.mp3", "_ptbr.mp3"]:
        p = OUTPUTS_DIR / f"{job_id}{suffix}"
        if p.exists():
            audio_path = p
            break

    if not audio_path:
        return None, "Arquivo de áudio não encontrado"

    # Obtém informações do áudio
    audio_size = audio_path.stat().st_size
    duration = get_audio_duration(audio_path)

    # Gera GUID estável
    guid = f"laris-{job_id}-{collection.slug}"

    # URL pública do áudio
    audio_url = f"{base_url}/api/podcast/{collection.slug}/episodes/{job_id}/audio.mp3"

    # Cria episódio
    episode = Episode(
        id=str(uuid.uuid4())[:8],
        collection_id=collection_id,
        title=title,
        description=description,
        audio_url=audio_url,
        audio_size=audio_size,
        duration_seconds=duration,
        guid=guid,
        pub_date=datetime.utcnow()
    )

    # Salva
    episodes = load_episodes()
    episodes.append(episode)
    save_episodes(episodes)

    # Atualiza feed RSS
    regenerate_feed(collection.slug, base_url)

    logger.info(f"Episódio criado: {title} na coleção {collection.name}")
    return episode, None


def format_duration(seconds: int) -> str:
    """Formata duração para iTunes (HH:MM:SS)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def regenerate_feed(slug: str, base_url: str) -> bool:
    """Regenera o feed RSS de uma coleção."""
    collection = get_collection_by_slug(slug)
    if not collection:
        return False

    episodes = get_episodes_by_collection(collection.id)
    episodes.sort(key=lambda e: e.pub_date, reverse=True)  # Mais recente primeiro

    # Namespaces
    nsmap = {
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'atom': 'http://www.w3.org/2005/Atom'
    }

    # Root
    rss = ET.Element('rss', {
        'version': '2.0',
        'xmlns:itunes': nsmap['itunes'],
        'xmlns:content': nsmap['content'],
        'xmlns:atom': nsmap['atom']
    })

    channel = ET.SubElement(rss, 'channel')

    # Metadados do canal
    ET.SubElement(channel, 'title').text = collection.name
    ET.SubElement(channel, 'description').text = collection.description or f"Artigos em áudio - {collection.name}"
    ET.SubElement(channel, 'link').text = base_url
    ET.SubElement(channel, 'language').text = collection.language
    ET.SubElement(channel, 'copyright').text = f"© {datetime.now().year} {collection.author}"
    ET.SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # iTunes tags
    ET.SubElement(channel, '{%s}author' % nsmap['itunes']).text = collection.author
    ET.SubElement(channel, '{%s}summary' % nsmap['itunes']).text = collection.description or collection.name
    ET.SubElement(channel, '{%s}explicit' % nsmap['itunes']).text = 'no'
    ET.SubElement(channel, '{%s}type' % nsmap['itunes']).text = 'episodic'

    owner = ET.SubElement(channel, '{%s}owner' % nsmap['itunes'])
    ET.SubElement(owner, '{%s}name' % nsmap['itunes']).text = collection.author
    ET.SubElement(owner, '{%s}email' % nsmap['itunes']).text = collection.email

    # Categoria (Education > Self-Improvement)
    category = ET.SubElement(channel, '{%s}category' % nsmap['itunes'], text='Education')
    ET.SubElement(category, '{%s}category' % nsmap['itunes'], text='Self-Improvement')

    # Imagem
    if collection.image_url:
        ET.SubElement(channel, '{%s}image' % nsmap['itunes'], href=collection.image_url)
    else:
        # Imagem padrão
        ET.SubElement(channel, '{%s}image' % nsmap['itunes'], href=f"{base_url}/static/podcast-cover.jpg")

    # Atom self link
    feed_url = f"{base_url}/api/podcast/{slug}/feed.xml"
    ET.SubElement(channel, '{%s}link' % nsmap['atom'], {
        'href': feed_url,
        'rel': 'self',
        'type': 'application/rss+xml'
    })

    # Episódios
    for ep in episodes:
        item = ET.SubElement(channel, 'item')

        ET.SubElement(item, 'title').text = ep.title
        ET.SubElement(item, 'description').text = ep.description or ep.title
        ET.SubElement(item, '{%s}summary' % nsmap['itunes']).text = ep.description or ep.title
        ET.SubElement(item, 'guid', isPermaLink='false').text = ep.guid
        ET.SubElement(item, 'pubDate').text = ep.pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')

        # Enclosure (o áudio)
        ET.SubElement(item, 'enclosure', {
            'url': ep.audio_url,
            'length': str(ep.audio_size),
            'type': 'audio/mpeg'
        })

        # iTunes específico
        ET.SubElement(item, '{%s}duration' % nsmap['itunes']).text = format_duration(ep.duration_seconds)
        ET.SubElement(item, '{%s}explicit' % nsmap['itunes']).text = 'no'
        ET.SubElement(item, '{%s}episodeType' % nsmap['itunes']).text = 'full'

        if ep.image_url:
            ET.SubElement(item, '{%s}image' % nsmap['itunes'], href=ep.image_url)

    # Gera XML formatado
    xml_str = ET.tostring(rss, encoding='unicode')

    # Adiciona declaração XML
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    # Formata com indentação
    try:
        dom = minidom.parseString(xml_str)
        xml_str = dom.toprettyxml(indent="  ", encoding=None)
        # Remove linha extra do toprettyxml
        xml_str = '\n'.join(line for line in xml_str.split('\n') if line.strip())
    except Exception:
        pass  # Mantém não formatado se falhar

    # Salva arquivo
    feed_dir = PODCAST_DIR / "feeds"
    feed_dir.mkdir(exist_ok=True)
    feed_path = feed_dir / f"{slug}.xml"

    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    logger.info(f"Feed RSS regenerado: {feed_path}")
    return True


def get_feed_path(slug: str) -> Optional[Path]:
    """Retorna o caminho do arquivo de feed."""
    feed_path = PODCAST_DIR / "feeds" / f"{slug}.xml"
    if feed_path.exists():
        return feed_path
    return None


def get_episode_audio_path(slug: str, job_id: str) -> Optional[Path]:
    """Retorna o caminho do áudio de um episódio."""
    # Verifica se a coleção existe
    collection = get_collection_by_slug(slug)
    if not collection:
        return None

    # Busca o arquivo
    for suffix in ["_final.mp3", "_ptbr.mp3"]:
        p = OUTPUTS_DIR / f"{job_id}{suffix}"
        if p.exists():
            return p

    return None
