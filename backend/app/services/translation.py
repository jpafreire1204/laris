"""
Laris - Translation Service
Tradução de textos usando Argos Translate (offline).
"""

import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


def check_translation_packages() -> Tuple[bool, List[str], List[str]]:
    """
    Verifica quais pacotes de tradução estão instalados.

    Returns:
        Tupla (en_to_pt_installed, idiomas_disponíveis, idiomas_necessários)
    """
    try:
        import argostranslate.package
        import argostranslate.translate

        # Atualiza lista de pacotes disponíveis
        argostranslate.package.update_package_index()

        # Lista pacotes instalados
        installed_packages = argostranslate.translate.get_installed_languages()
        installed_codes = [lang.code for lang in installed_packages]

        logger.info(f"Idiomas instalados: {installed_codes}")

        # Verifica se temos EN -> PT
        en_to_pt = False
        for lang in installed_packages:
            if lang.code == 'en':
                translations = lang.get_translation(
                    argostranslate.translate.get_language_from_code('pt')
                )
                if translations:
                    en_to_pt = True
                    break

        needs_download = []
        if not en_to_pt:
            needs_download.append('en-pt')

        return en_to_pt, installed_codes, needs_download

    except Exception as e:
        logger.error(f"Erro ao verificar pacotes: {e}")
        return False, [], ['en-pt']


def install_translation_package(from_code: str = 'en', to_code: str = 'pt') -> Tuple[bool, str]:
    """
    Instala um pacote de tradução.

    Args:
        from_code: Código do idioma de origem
        to_code: Código do idioma de destino

    Returns:
        Tupla (sucesso, mensagem)
    """
    try:
        import argostranslate.package
        import argostranslate.translate

        logger.info(f"Instalando pacote de tradução: {from_code} -> {to_code}")

        # Atualiza índice de pacotes
        argostranslate.package.update_package_index()

        # Obtém pacotes disponíveis
        available_packages = argostranslate.package.get_available_packages()

        # Encontra o pacote correto
        package_to_install = None
        for pkg in available_packages:
            if pkg.from_code == from_code and pkg.to_code == to_code:
                package_to_install = pkg
                break

        if not package_to_install:
            return False, f"Pacote {from_code}->{to_code} não encontrado."

        # Baixa e instala
        logger.info("Baixando pacote de tradução... Isso pode levar alguns minutos.")
        download_path = package_to_install.download()
        argostranslate.package.install_from_path(download_path)

        logger.info("Pacote instalado com sucesso!")
        return True, f"Pacote de tradução {from_code} -> {to_code} instalado com sucesso!"

    except Exception as e:
        error_msg = f"Erro ao instalar pacote: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def translate_text(text: str, from_code: str = 'en', to_code: str = 'pt') -> Tuple[Optional[str], str]:
    """
    Traduz texto de um idioma para outro.

    Args:
        text: Texto para traduzir
        from_code: Código do idioma de origem
        to_code: Código do idioma de destino

    Returns:
        Tupla (texto_traduzido, mensagem_de_erro)
    """
    if not text or not text.strip():
        return None, "Texto vazio para traduzir."

    try:
        import argostranslate.translate

        # Obtém os idiomas instalados
        from_lang = argostranslate.translate.get_language_from_code(from_code)
        to_lang = argostranslate.translate.get_language_from_code(to_code)

        if not from_lang:
            return None, f"Idioma de origem '{from_code}' não instalado. Instale o pacote de tradução."

        if not to_lang:
            return None, f"Idioma de destino '{to_code}' não instalado. Instale o pacote de tradução."

        # Obtém a tradução
        translation = from_lang.get_translation(to_lang)

        if not translation:
            return None, (
                f"Tradução de {from_code} para {to_code} não disponível. "
                "Por favor, instale o pacote de tradução."
            )

        # Traduz preservando parágrafos
        paragraphs = text.split('\n\n')
        translated_paragraphs = []

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # Traduz linhas individuais dentro do parágrafo para preservar quebras
                lines = paragraph.split('\n')
                translated_lines = []

                for line in lines:
                    if line.strip():
                        translated_line = translation.translate(line.strip())
                        translated_lines.append(translated_line)
                    else:
                        translated_lines.append('')

                translated_paragraphs.append('\n'.join(translated_lines))
            else:
                translated_paragraphs.append('')

            # Log de progresso para textos longos
            if len(paragraphs) > 10 and (i + 1) % 10 == 0:
                logger.info(f"Tradução: {i + 1}/{len(paragraphs)} parágrafos")

        translated_text = '\n\n'.join(translated_paragraphs)
        return translated_text.strip(), ""

    except ImportError:
        return None, (
            "Argos Translate não está instalado corretamente. "
            "Por favor, reinstale as dependências."
        )

    except Exception as e:
        error_msg = f"Erro na tradução: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def get_supported_language_pairs() -> List[Tuple[str, str]]:
    """
    Lista pares de idiomas suportados para tradução.

    Returns:
        Lista de tuplas (from_code, to_code)
    """
    # Pares mais comuns para artigos científicos
    return [
        ('en', 'pt'),  # Inglês -> Português
        ('es', 'pt'),  # Espanhol -> Português (pode não estar disponível)
        ('fr', 'pt'),  # Francês -> Português (pode não estar disponível)
        ('de', 'pt'),  # Alemão -> Português (pode não estar disponível)
    ]
