"""
Laris - Language Detection Service
Detecta o idioma do texto.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mapeamento de códigos de idioma para nomes em português
LANGUAGE_NAMES = {
    'pt': 'Português',
    'en': 'Inglês',
    'es': 'Espanhol',
    'fr': 'Francês',
    'de': 'Alemão',
    'it': 'Italiano',
    'nl': 'Holandês',
    'ru': 'Russo',
    'zh-cn': 'Chinês (Simplificado)',
    'zh-tw': 'Chinês (Tradicional)',
    'ja': 'Japonês',
    'ko': 'Coreano',
    'ar': 'Árabe',
    'hi': 'Hindi',
    'pl': 'Polonês',
    'tr': 'Turco',
    'vi': 'Vietnamita',
    'th': 'Tailandês',
    'sv': 'Sueco',
    'da': 'Dinamarquês',
    'no': 'Norueguês',
    'fi': 'Finlandês',
    'cs': 'Tcheco',
    'ro': 'Romeno',
    'hu': 'Húngaro',
    'el': 'Grego',
    'he': 'Hebraico',
    'id': 'Indonésio',
    'uk': 'Ucraniano',
    'bg': 'Búlgaro',
    'ca': 'Catalão',
}


def detect_language(text: str) -> Optional[str]:
    """
    Detecta o idioma do texto.

    Args:
        text: Texto para analisar

    Returns:
        Código do idioma (ex: 'en', 'pt') ou None em caso de erro
    """
    if not text or len(text.strip()) < 10:
        return None

    try:
        from langdetect import detect, DetectorFactory

        # Torna a detecção determinística
        DetectorFactory.seed = 0

        # Usa uma amostra do texto para detecção mais rápida
        sample = text[:5000] if len(text) > 5000 else text

        detected = detect(sample)
        logger.info(f"Idioma detectado: {detected}")
        return detected

    except Exception as e:
        logger.error(f"Erro na detecção de idioma: {e}")
        return None


def get_language_name(code: str) -> str:
    """
    Retorna o nome do idioma em português.

    Args:
        code: Código do idioma (ex: 'en')

    Returns:
        Nome do idioma em português
    """
    return LANGUAGE_NAMES.get(code.lower(), f"Idioma desconhecido ({code})")


def is_portuguese(code: str) -> bool:
    """
    Verifica se o código representa português.

    Args:
        code: Código do idioma

    Returns:
        True se for português
    """
    if not code:
        return False
    return code.lower() in ('pt', 'pt-br', 'pt-pt')


def needs_translation(code: str) -> bool:
    """
    Verifica se o texto precisa de tradução para português.

    Args:
        code: Código do idioma detectado

    Returns:
        True se precisar de tradução
    """
    return not is_portuguese(code)
