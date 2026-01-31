"""
Testes para o módulo de chunking de texto.
"""

import pytest
from app.utils.chunking import (
    split_text_into_chunks,
    estimate_audio_duration,
    count_words,
    count_paragraphs
)


class TestSplitTextIntoChunks:
    """Testes para divisão de texto em chunks."""

    def test_short_text_single_chunk(self):
        """Texto curto deve resultar em um único chunk."""
        text = "Este é um texto curto."
        chunks = split_text_into_chunks(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        """Texto vazio deve resultar em lista vazia."""
        chunks = split_text_into_chunks("")
        assert chunks == []

    def test_long_text_multiple_chunks(self):
        """Texto longo deve ser dividido em múltiplos chunks."""
        text = "Esta é uma frase. " * 200  # ~3600 caracteres
        chunks = split_text_into_chunks(text, max_chars=1000)
        assert len(chunks) > 1

    def test_chunks_respect_max_size(self):
        """Cada chunk deve respeitar o tamanho máximo."""
        text = "Esta é uma frase longa para teste. " * 100
        max_chars = 500
        chunks = split_text_into_chunks(text, max_chars=max_chars)

        for chunk in chunks:
            # Pequena tolerância para cortes em pontos naturais
            assert len(chunk) <= max_chars + 100

    def test_preserves_paragraph_breaks(self):
        """Deve tentar preservar quebras de parágrafo."""
        text = "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três."
        chunks = split_text_into_chunks(text, max_chars=30)

        # Verifica que não cortou no meio de palavras
        for chunk in chunks:
            assert not chunk.startswith(' ')
            assert not chunk.endswith(' ')

    def test_cuts_at_sentence_end(self):
        """Deve preferir cortar no fim de frases."""
        text = "Primeira frase. Segunda frase. Terceira frase. Quarta frase."
        chunks = split_text_into_chunks(text, max_chars=35)

        for chunk in chunks[:-1]:  # Exceto o último
            # Deve terminar com pontuação
            stripped = chunk.strip()
            if stripped:
                assert stripped[-1] in '.!?'


class TestEstimateAudioDuration:
    """Testes para estimativa de duração do áudio."""

    def test_empty_text_zero_duration(self):
        """Texto vazio deve ter duração zero."""
        duration = estimate_audio_duration("")
        assert duration == 0

    def test_normal_speed(self):
        """Velocidade normal (1.0)."""
        # 150 palavras = 1 minuto = 60 segundos
        text = "palavra " * 150
        duration = estimate_audio_duration(text, speed=1.0)
        assert 55 <= duration <= 65  # ~60 segundos

    def test_faster_speed(self):
        """Velocidade mais rápida reduz duração."""
        text = "palavra " * 150
        duration_normal = estimate_audio_duration(text, speed=1.0)
        duration_fast = estimate_audio_duration(text, speed=1.5)
        assert duration_fast < duration_normal

    def test_slower_speed(self):
        """Velocidade mais lenta aumenta duração."""
        text = "palavra " * 150
        duration_normal = estimate_audio_duration(text, speed=1.0)
        duration_slow = estimate_audio_duration(text, speed=0.75)
        assert duration_slow > duration_normal


class TestCountWords:
    """Testes para contagem de palavras."""

    def test_count_simple(self):
        """Contagem simples de palavras."""
        assert count_words("uma duas três") == 3

    def test_count_empty(self):
        """Texto vazio tem zero palavras."""
        assert count_words("") == 0

    def test_count_with_punctuation(self):
        """Pontuação não deve afetar contagem."""
        assert count_words("Olá, mundo!") == 2


class TestCountParagraphs:
    """Testes para contagem de parágrafos."""

    def test_count_paragraphs(self):
        """Conta parágrafos separados por linha dupla."""
        text = "Parágrafo 1.\n\nParágrafo 2.\n\nParágrafo 3."
        assert count_paragraphs(text) == 3

    def test_single_paragraph(self):
        """Texto sem quebra dupla é um parágrafo."""
        assert count_paragraphs("Texto simples sem quebras.") == 1

    def test_empty_text(self):
        """Texto vazio tem zero parágrafos."""
        assert count_paragraphs("") == 0
