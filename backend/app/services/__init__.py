# Services module
from .extraction import extract_text_from_file
from .language_detection import detect_language, get_language_name
from .translation import translate_text, check_translation_packages, install_translation_package
from .tts_service import generate_audio, get_available_voices, speed_to_rate

__all__ = [
    "extract_text_from_file",
    "detect_language",
    "get_language_name",
    "translate_text",
    "check_translation_packages",
    "install_translation_package",
    "generate_audio",
    "get_available_voices",
    "speed_to_rate"
]
