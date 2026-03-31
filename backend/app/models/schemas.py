"""
Laris - Pydantic schemas.
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status de processamento de um job."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    TRANSLATING = "translating"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    ERROR = "error"


class ExtractResponse(BaseModel):
    """Resposta da extracao de texto."""

    success: bool
    text: str = ""
    preview: str = ""
    detected_language: str = ""
    language_name: str = ""
    is_portuguese: bool = False
    char_count: int = 0
    error: Optional[str] = None
    file_id: Optional[str] = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    """Requisicao de traducao."""

    text: str
    source_language: str = "en"


class TranslateResponse(BaseModel):
    """Resposta da traducao."""

    success: bool
    original_text: str = ""
    translated_text: str = ""
    source_language: str = ""
    target_language: str = "pt"
    error: Optional[str] = None


class VoiceInfo(BaseModel):
    """Informacoes de uma voz disponivel."""

    id: str
    name: str
    gender: str
    locale: str


class VoicesResponse(BaseModel):
    """Lista de vozes disponiveis."""

    voices: List[VoiceInfo]


class TTSRequest(BaseModel):
    """Requisicao de geracao de audio."""

    text: str
    voice_id: str = "pt-BR-FranciscaNeural"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    file_id: Optional[str] = None
    skip_translation: bool = False
    filename: Optional[str] = None
    include_references: bool = False


class TTSResponse(BaseModel):
    """Resposta de criacao do job de TTS."""

    success: bool
    job_id: str = ""
    status: JobStatus = JobStatus.PENDING
    audio_url: Optional[str] = None
    text_url: Optional[str] = None
    error: Optional[str] = None


class AudioMode(str, Enum):
    """Modo do audio retornado."""

    SINGLE = "single"
    PARTS = "parts"


class JobStatusResponse(BaseModel):
    """Status atual de um job."""

    job_id: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    audio_url: Optional[str] = None
    audio_mode: AudioMode = AudioMode.SINGLE
    text_url: Optional[str] = None
    pdf_url: Optional[str] = None
    error: Optional[str] = None
    stage: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    detected_language: Optional[str] = None
    language_name: Optional[str] = None
    translation_skipped: Optional[bool] = None


class TranslationPackageStatus(BaseModel):
    """Status dos pacotes de traducao instalados."""

    installed: bool
    available_languages: List[str]
    needs_download: List[str]


class InstallPackageRequest(BaseModel):
    """Requisicao para instalar pacote de traducao."""

    from_code: str = "en"
    to_code: str = "pt"


class InstallPackageResponse(BaseModel):
    """Resposta da instalacao de pacote."""

    success: bool
    message: str
    error: Optional[str] = None
