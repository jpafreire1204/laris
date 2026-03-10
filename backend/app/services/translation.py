"""
Laris - Translation Service
Tradução de textos usando Google Translate (via deep-translator).
Mais confiável e não requer instalação de modelos.
"""

import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Cache para verificar disponibilidade
_translator_available: Optional[bool] = None


def check_translator_available() -> bool:
    """Verifica se o deep-translator está disponível."""
    global _translator_available
    if _translator_available is None:
        try:
            from deep_translator import GoogleTranslator
            # Testa uma tradução simples
            translator = GoogleTranslator(source='en', target='pt')
            result = translator.translate("test")
            _translator_available = result is not None
        except Exception as e:
            logger.warning(f"deep-translator não disponível: {e}")
            _translator_available = False
    return _translator_available


def check_translation_packages() -> Tuple[bool, List[str], List[str]]:
    """
    Verifica status do serviço de tradução.

    Returns:
        Tupla (disponível, idiomas_suportados, idiomas_necessários)
    """
    available = check_translator_available()

    if available:
        # Google Translate suporta muitos idiomas
        supported = ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'ru', 'zh', 'ja', 'ko']
        return True, supported, []
    else:
        return False, [], ['deep-translator']


def install_translation_package(from_code: str = 'en', to_code: str = 'pt') -> Tuple[bool, str]:
    """
    Com Google Translate, não precisa instalar pacotes.
    Este método existe para compatibilidade com a API antiga.
    """
    if check_translator_available():
        return True, "Google Translate já está disponível. Não precisa instalar nada."
    else:
        return False, (
            "deep-translator não está instalado. "
            "Execute: pip install deep-translator"
        )


def translate_text(
    text: str,
    from_code: str = 'en',
    to_code: str = 'pt',
    progress_callback=None
) -> Tuple[Optional[str], str]:
    """
    Traduz texto usando Google Translate.

    Args:
        text: Texto para traduzir
        from_code: Código do idioma de origem (auto para detectar)
        to_code: Código do idioma de destino
        progress_callback: Função callback(current, total) para atualizar progresso

    Returns:
        Tupla (texto_traduzido, mensagem_de_erro)
    """
    if not text or not text.strip():
        return None, "Texto vazio para traduzir."

    try:
        from deep_translator import GoogleTranslator

        logger.info(f"[TRANSLATE] Iniciando tradução: {from_code} -> {to_code}")
        logger.info(f"[TRANSLATE] Texto original: {len(text)} caracteres")

        # Normaliza código de idioma
        source_lang = 'auto' if from_code == 'unknown' else from_code
        if source_lang.startswith('zh'):
            source_lang = 'zh-CN'

        # Google Translate tem limite de 5000 caracteres por requisição
        # Divide o texto em partes se necessário
        MAX_CHARS = 4500  # Um pouco abaixo do limite para segurança

        if len(text) <= MAX_CHARS:
            # Texto pequeno, traduz direto
            translator = GoogleTranslator(source=source_lang, target=to_code)
            translated = translator.translate(text)

            if not translated:
                return None, "Tradução retornou vazio"

            logger.info(f"[TRANSLATE] Tradução concluída: {len(translated)} caracteres")
            return translated.strip(), ""

        else:
            # Texto grande, divide em partes preservando parágrafos
            logger.info(f"[TRANSLATE] Texto grande, dividindo em partes...")

            paragraphs = text.split('\n\n')
            translated_parts = []
            current_batch = ""
            batch_count = 0

            # Estima o número total de batches para o progresso
            total_chars = len(text)
            estimated_batches = max(1, (total_chars // MAX_CHARS) + 1)

            translator = GoogleTranslator(source=source_lang, target=to_code)

            for i, paragraph in enumerate(paragraphs):
                # Se adicionar este parágrafo exceder o limite, traduz o batch atual
                if len(current_batch) + len(paragraph) + 2 > MAX_CHARS:
                    if current_batch:
                        batch_count += 1
                        logger.info(f"[TRANSLATE] Traduzindo batch {batch_count}...")

                        # Chama callback de progresso
                        if progress_callback:
                            progress_callback(batch_count, estimated_batches)

                        translated_batch = translator.translate(current_batch)
                        if translated_batch:
                            translated_parts.append(translated_batch)

                        current_batch = paragraph
                    else:
                        # Parágrafo único muito grande, traduz sozinho
                        batch_count += 1
                        logger.info(f"[TRANSLATE] Traduzindo parágrafo grande {batch_count}...")

                        # Chama callback de progresso
                        if progress_callback:
                            progress_callback(batch_count, estimated_batches)

                        # Divide o parágrafo em sentenças se necessário
                        if len(paragraph) > MAX_CHARS:
                            sentences = paragraph.replace('. ', '.|').split('|')
                            for sentence in sentences:
                                if sentence.strip():
                                    trans = translator.translate(sentence.strip())
                                    if trans:
                                        translated_parts.append(trans)
                        else:
                            translated_batch = translator.translate(paragraph)
                            if translated_batch:
                                translated_parts.append(translated_batch)

                        current_batch = ""
                else:
                    if current_batch:
                        current_batch += "\n\n" + paragraph
                    else:
                        current_batch = paragraph

                # Log de progresso
                if len(paragraphs) > 20 and (i + 1) % 20 == 0:
                    logger.info(f"[TRANSLATE] Progresso: {i + 1}/{len(paragraphs)} parágrafos")

            # Traduz o último batch
            if current_batch:
                batch_count += 1
                logger.info(f"[TRANSLATE] Traduzindo batch final {batch_count}...")

                # Chama callback de progresso final
                if progress_callback:
                    progress_callback(batch_count, batch_count)

                translated_batch = translator.translate(current_batch)
                if translated_batch:
                    translated_parts.append(translated_batch)

            translated_text = '\n\n'.join(translated_parts)

            logger.info(f"[TRANSLATE] Tradução completa: {len(translated_text)} caracteres em {batch_count} batches")
            return translated_text.strip(), ""

    except ImportError:
        return None, (
            "deep-translator não está instalado. "
            "Execute: pip install deep-translator"
        )

    except Exception as e:
        error_msg = f"Erro na tradução: {str(e)}"
        logger.error(f"[TRANSLATE] {error_msg}")
        return None, error_msg


def get_supported_language_pairs() -> List[Tuple[str, str]]:
    """
    Lista pares de idiomas suportados para tradução.
    Google Translate suporta praticamente qualquer par.

    Returns:
        Lista de tuplas (from_code, to_code)
    """
    return [
        ('en', 'pt'),  # Inglês -> Português
        ('es', 'pt'),  # Espanhol -> Português
        ('fr', 'pt'),  # Francês -> Português
        ('de', 'pt'),  # Alemão -> Português
        ('it', 'pt'),  # Italiano -> Português
        ('nl', 'pt'),  # Holandês -> Português
        ('ru', 'pt'),  # Russo -> Português
        ('zh-CN', 'pt'),  # Chinês -> Português
        ('ja', 'pt'),  # Japonês -> Português
        ('ko', 'pt'),  # Coreano -> Português
    ]
