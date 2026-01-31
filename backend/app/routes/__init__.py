# Routes module
from .extract import router as extract_router
from .translate import router as translate_router
from .tts import router as tts_router
from .voices import router as voices_router

__all__ = [
    "extract_router",
    "translate_router",
    "tts_router",
    "voices_router"
]
