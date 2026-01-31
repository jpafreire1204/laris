"""
Laris - Translate Route
Endpoints para tradução de texto.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    TranslateRequest,
    TranslateResponse,
    TranslationPackageStatus,
    InstallPackageRequest,
    InstallPackageResponse
)
from app.services.translation import (
    translate_text,
    check_translation_packages,
    install_translation_package
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    Traduz texto para português brasileiro.
    """
    if not request.text or not request.text.strip():
        return TranslateResponse(
            success=False,
            error="Texto vazio para traduzir."
        )

    logger.info(f"Traduzindo texto: {len(request.text)} caracteres, de {request.source_language}")

    translated, error = translate_text(
        text=request.text,
        from_code=request.source_language,
        to_code="pt"
    )

    if error:
        return TranslateResponse(
            success=False,
            original_text=request.text,
            source_language=request.source_language,
            error=error
        )

    return TranslateResponse(
        success=True,
        original_text=request.text,
        translated_text=translated,
        source_language=request.source_language,
        target_language="pt"
    )


@router.get("/translate/status", response_model=TranslationPackageStatus)
async def get_translation_status():
    """
    Verifica status dos pacotes de tradução instalados.
    """
    installed, available, needs_download = check_translation_packages()

    return TranslationPackageStatus(
        installed=installed,
        available_languages=available,
        needs_download=needs_download
    )


@router.post("/translate/install", response_model=InstallPackageResponse)
async def install_package(request: InstallPackageRequest):
    """
    Instala um pacote de tradução.

    Este processo pode levar alguns minutos para baixar o modelo.
    """
    logger.info(f"Instalando pacote: {request.from_code} -> {request.to_code}")

    success, message = install_translation_package(
        from_code=request.from_code,
        to_code=request.to_code
    )

    if success:
        return InstallPackageResponse(
            success=True,
            message=message
        )
    else:
        return InstallPackageResponse(
            success=False,
            message="Falha na instalação",
            error=message
        )
