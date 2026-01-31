"""
Testes para o serviço de extração de texto.
"""

import pytest
from app.services.extraction import get_text_preview
from app.services.language_detection import detect_language, get_language_name, is_portuguese


class TestTextPreview:
    """Testes para geração de prévia de texto."""

    def test_short_text_unchanged(self):
        """Texto curto deve permanecer inalterado."""
        text = "Este é um texto curto."
        preview = get_text_preview(text, max_chars=1500)
        assert preview == text

    def test_long_text_truncated(self):
        """Texto longo deve ser truncado."""
        text = "A" * 2000
        preview = get_text_preview(text, max_chars=1500)
        assert len(preview) < 2000
        assert "[...]" in preview

    def test_cuts_at_natural_point(self):
        """Deve cortar em ponto natural (fim de frase)."""
        text = "Primeira frase. Segunda frase. " * 100
        preview = get_text_preview(text, max_chars=100)
        # Deve terminar com ponto ou [...]
        assert preview.endswith('.') or preview.endswith('[...]')


class TestLanguageDetection:
    """Testes para detecção de idioma."""

    def test_detect_english(self):
        """Deve detectar inglês."""
        text = "This is a sample text written in English for testing purposes."
        lang = detect_language(text)
        assert lang == "en"

    def test_detect_portuguese(self):
        """Deve detectar português."""
        text = "Este é um texto de exemplo escrito em português para testes."
        lang = detect_language(text)
        assert lang == "pt"

    def test_detect_spanish(self):
        """Deve detectar espanhol."""
        text = "Este es un texto de ejemplo escrito en español para pruebas."
        lang = detect_language(text)
        assert lang == "es"

    def test_empty_text(self):
        """Texto vazio deve retornar None."""
        lang = detect_language("")
        assert lang is None

    def test_short_text(self):
        """Texto muito curto deve retornar None."""
        lang = detect_language("Hi")
        assert lang is None


class TestLanguageNames:
    """Testes para nomes de idiomas."""

    def test_english_name(self):
        """Nome de inglês em português."""
        assert get_language_name("en") == "Inglês"

    def test_portuguese_name(self):
        """Nome de português em português."""
        assert get_language_name("pt") == "Português"

    def test_unknown_language(self):
        """Idioma desconhecido."""
        name = get_language_name("xyz")
        assert "xyz" in name
        assert "desconhecido" in name.lower()


class TestIsPortuguese:
    """Testes para verificação de português."""

    def test_pt_is_portuguese(self):
        """pt é português."""
        assert is_portuguese("pt") is True

    def test_pt_br_is_portuguese(self):
        """pt-br é português."""
        assert is_portuguese("pt-br") is True

    def test_en_is_not_portuguese(self):
        """en não é português."""
        assert is_portuguese("en") is False

    def test_none_is_not_portuguese(self):
        """None não é português."""
        assert is_portuguese(None) is False
