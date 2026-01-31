"""
Laris - Voices Route
Endpoint para listar vozes disponíveis.
"""

from fastapi import APIRouter

from app.models.schemas import VoicesResponse, VoiceInfo
from app.services.tts_service import get_available_voices

router = APIRouter()


@router.get("/voices", response_model=VoicesResponse)
async def list_voices():
    """
    Lista as vozes PT-BR disponíveis para narração.
    """
    voices_data = get_available_voices()

    voices = [
        VoiceInfo(
            id=v["id"],
            name=v["name"],
            gender=v["gender"],
            locale=v["locale"]
        )
        for v in voices_data
    ]

    return VoicesResponse(voices=voices)
