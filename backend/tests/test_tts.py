"""
Testes para o serviço de TTS.
"""

import pytest
from app.services.tts_service import speed_to_rate, get_available_voices


class TestSpeedToRate:
    """Testes para conversão de velocidade para rate."""

    def test_normal_speed(self):
        """Velocidade normal (1.0) = +0%."""
        assert speed_to_rate(1.0) == "+0%"

    def test_faster_speed(self):
        """Velocidade maior que 1.0."""
        assert speed_to_rate(1.5) == "+50%"
        assert speed_to_rate(1.25) == "+25%"
        assert speed_to_rate(2.0) == "+100%"

    def test_slower_speed(self):
        """Velocidade menor que 1.0."""
        assert speed_to_rate(0.75) == "-25%"
        assert speed_to_rate(0.5) == "-50%"

    def test_edge_cases(self):
        """Casos extremos."""
        assert speed_to_rate(1.1) == "+10%"
        assert speed_to_rate(0.9) == "-10%"


class TestGetAvailableVoices:
    """Testes para listagem de vozes."""

    def test_returns_list(self):
        """Deve retornar uma lista."""
        voices = get_available_voices()
        assert isinstance(voices, list)

    def test_has_voices(self):
        """Deve ter pelo menos uma voz."""
        voices = get_available_voices()
        assert len(voices) >= 1

    def test_voice_structure(self):
        """Cada voz deve ter a estrutura correta."""
        voices = get_available_voices()
        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "gender" in voice
            assert "locale" in voice

    def test_has_female_voice(self):
        """Deve ter pelo menos uma voz feminina."""
        voices = get_available_voices()
        female_voices = [v for v in voices if v["gender"] == "Feminino"]
        assert len(female_voices) >= 1

    def test_has_male_voice(self):
        """Deve ter pelo menos uma voz masculina."""
        voices = get_available_voices()
        male_voices = [v for v in voices if v["gender"] == "Masculino"]
        assert len(male_voices) >= 1

    def test_all_ptbr_locale(self):
        """Todas as vozes devem ser pt-BR."""
        voices = get_available_voices()
        for voice in voices:
            assert voice["locale"] == "pt-BR"


class TestVoiceIds:
    """Testes para IDs de vozes."""

    def test_francisca_available(self):
        """Voz Francisca (feminina padrão) deve estar disponível."""
        voices = get_available_voices()
        ids = [v["id"] for v in voices]
        assert "pt-BR-FranciscaNeural" in ids

    def test_antonio_available(self):
        """Voz Antonio (masculina) deve estar disponível."""
        voices = get_available_voices()
        ids = [v["id"] for v in voices]
        assert "pt-BR-AntonioNeural" in ids
