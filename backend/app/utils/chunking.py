"""
Laris - Text Chunking Utilities
Divide textos longos em chunks para processamento do TTS.
"""

import re
from typing import List


def split_text_into_chunks(text: str, max_chars: int = 3000) -> List[str]:
    """
    Divide o texto em chunks menores para processamento do TTS.

    Tenta dividir em pontos naturais (fim de parágrafo, fim de frase)
    para manter a fluidez da narração.

    Args:
        text: Texto completo para dividir
        max_chars: Tamanho máximo de cada chunk (padrão: 3000 caracteres)

    Returns:
        Lista de chunks de texto
    """
    if not text or len(text) <= max_chars:
        return [text] if text else []

    chunks: List[str] = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining.strip())
            break

        # Tenta encontrar um ponto de corte natural
        chunk = remaining[:max_chars]

        # Primeiro, tenta cortar no fim de um parágrafo
        last_paragraph = chunk.rfind('\n\n')
        if last_paragraph > max_chars // 2:
            cut_point = last_paragraph + 2
        else:
            # Tenta cortar no fim de uma frase
            # Procura por . ! ? seguido de espaço ou fim
            sentence_end_pattern = r'[.!?]\s+'
            matches = list(re.finditer(sentence_end_pattern, chunk))

            if matches:
                # Usa o último match que está na segunda metade do chunk
                valid_matches = [m for m in matches if m.end() > max_chars // 2]
                if valid_matches:
                    cut_point = valid_matches[-1].end()
                else:
                    cut_point = matches[-1].end()
            else:
                # Último recurso: corta no último espaço
                last_space = chunk.rfind(' ')
                if last_space > max_chars // 2:
                    cut_point = last_space + 1
                else:
                    cut_point = max_chars

        # Adiciona o chunk e continua
        chunks.append(remaining[:cut_point].strip())
        remaining = remaining[cut_point:].strip()

    return chunks


def estimate_audio_duration(text: str, speed: float = 1.0) -> float:
    """
    Estima a duração do áudio em segundos.

    Assume ~150 palavras por minuto em velocidade normal.

    Args:
        text: Texto para narrar
        speed: Velocidade da fala (1.0 = normal)

    Returns:
        Duração estimada em segundos
    """
    words = len(text.split())
    base_wpm = 150  # Palavras por minuto
    adjusted_wpm = base_wpm * speed
    duration_minutes = words / adjusted_wpm
    return duration_minutes * 60


def count_words(text: str) -> int:
    """Conta o número de palavras no texto."""
    return len(text.split())


def count_paragraphs(text: str) -> int:
    """Conta o número de parágrafos no texto."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return len(paragraphs)
