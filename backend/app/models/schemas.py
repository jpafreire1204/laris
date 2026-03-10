"""
Laris - Pydantic Schemas
Modelos de dados para requisições e respostas da API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class JobStatus(str, Enum):
    """Status de processamento de um job."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    TRANSLATING = "translating"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    ERROR = "error"


class ExtractResponse(BaseModel):
    """Resposta da extração de texto."""
    success: bool
    text: str = ""
    preview: str = ""  # Primeiros ~1500 caracteres
    detected_language: str = ""
    language_name: str = ""
    is_portuguese: bool = False
    char_count: int = 0
    error: Optional[str] = None
    file_id: Optional[str] = None  # ID do PDF original (para manter layout)


class TranslateRequest(BaseModel):
    """Requisição de tradução."""
    text: str
    source_language: str = "en"  # Código do idioma fonte


class TranslateResponse(BaseModel):
    """Resposta da tradução."""
    success: bool
    original_text: str = ""
    translated_text: str = ""
    source_language: str = ""
    target_language: str = "pt"
    error: Optional[str] = None


class VoiceInfo(BaseModel):
    """Informações sobre uma voz disponível."""
    id: str
    name: str
    gender: str  # "Feminino" ou "Masculino"
    locale: str


class VoicesResponse(BaseModel):
    """Lista de vozes disponíveis."""
    voices: List[VoiceInfo]


class TTSRequest(BaseModel):
    """Requisição de geração de áudio."""
    text: str
    voice_id: str = "pt-BR-FranciscaNeural"  # Voz padrão feminina
    speed: float = Field(default=1.0, ge=0.5, le=2.0)  # 0.5x a 2x
    file_id: Optional[str] = None
    skip_translation: bool = False
    filename: Optional[str] = None


class TTSResponse(BaseModel):
    """Resposta da geração de áudio."""
    success: bool
    job_id: str = ""
    status: JobStatus = JobStatus.PENDING
    audio_url: Optional[str] = None
    text_url: Optional[str] = None
    error: Optional[str] = None


class AudioMode(str, Enum):
    """Modo de áudio gerado."""
    SINGLE = "single"  # MP3 único (pydub disponível)
    PARTS = "parts"    # ZIP com partes (fallback)


class JobStatusResponse(BaseModel):
    """Status de um job."""
    job_id: str
    status: JobStatus
    progress: int = 0  # 0-100
    message: str = ""
    audio_url: Optional[str] = None
    audio_mode: AudioMode = AudioMode.SINGLE  # sempre "single" agora
    text_url: Optional[str] = None
    pdf_url: Optional[str] = None
    error: Optional[str] = None
    # Campos de tradução
    detected_language: Optional[str] = None  # código do idioma (en, pt, es, etc.)
    language_name: Optional[str] = None  # nome do idioma (Inglês, Português, etc.)
    translation_skipped: Optional[bool] = None  # True se texto já era PT-BR


class TranslationPackageStatus(BaseModel):
    """Status dos pacotes de tradução instalados."""
    installed: bool
    available_languages: List[str]
    needs_download: List[str]


class InstallPackageRequest(BaseModel):
    """Requisição para instalar pacote de tradução."""
    from_code: str = "en"
    to_code: str = "pt"


class InstallPackageResponse(BaseModel):
    """Resposta da instalação de pacote."""
    success: bool
    message: str
    error: Optional[str] = None
