"""
Laris - File Utilities
Gerenciamento de arquivos e diretórios.
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Diretório base do projeto (2 níveis acima de app/utils)
BASE_DIR = Path(__file__).parent.parent.parent.parent


def get_outputs_dir() -> Path:
    """Resolve o diretÃ³rio de saÃ­da para ambiente local ou serverless."""
    custom_output_dir = os.environ.get("OUTPUTS_DIR")
    if custom_output_dir:
        return Path(custom_output_dir)

    if os.environ.get("VERCEL") or os.environ.get("RAILWAY_PROJECT_ID"):
        temp_root = Path(
            os.environ.get("VERCEL_TMPDIR")
            or os.environ.get("TMPDIR")
            or "/tmp"
        )
        return temp_root / "laris-outputs"

    return BASE_DIR / "outputs"


OUTPUTS_DIR = get_outputs_dir()


def ensure_outputs_dir() -> Path:
    """Garante que o diretório outputs existe."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos de nomes de arquivo."""
    # Remove caracteres especiais, mantém letras, números, hífens e underscores
    sanitized = re.sub(r'[^\w\-]', '_', name)
    # Remove underscores múltiplos
    sanitized = re.sub(r'_+', '_', sanitized)
    # Limita o tamanho
    return sanitized[:50].strip('_')


def generate_filename(original_name: str, suffix: str = "", extension: str = "mp3") -> str:
    """
    Gera um nome de arquivo único baseado no timestamp.

    Args:
        original_name: Nome original do arquivo
        suffix: Sufixo adicional (ex: "_ptbr")
        extension: Extensão do arquivo

    Returns:
        Nome do arquivo formatado
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = sanitize_filename(Path(original_name).stem)
    return f"{timestamp}_{base_name}{suffix}.{extension}"


def save_job_metadata(job_id: str, metadata: Dict[str, Any]) -> None:
    """Salva metadados de um job em arquivo JSON."""
    ensure_outputs_dir()
    metadata_file = OUTPUTS_DIR / f"{job_id}_metadata.json"

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)


def load_job_metadata(job_id: str) -> Optional[Dict[str, Any]]:
    """Carrega metadados de um job."""
    metadata_file = OUTPUTS_DIR / f"{job_id}_metadata.json"

    if not metadata_file.exists():
        return None

    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def cleanup_old_files(max_age_hours: int = 24) -> int:
    """
    Remove arquivos antigos do diretório outputs.

    Args:
        max_age_hours: Idade máxima em horas

    Returns:
        Número de arquivos removidos
    """
    if not OUTPUTS_DIR.exists():
        return 0

    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed = 0

    for file_path in OUTPUTS_DIR.iterdir():
        if file_path.is_file():
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    file_path.unlink()
                    removed += 1
                    logger.info(f"Arquivo antigo removido: {file_path.name}")
            except Exception as e:
                logger.error(f"Erro ao remover {file_path}: {e}")

    return removed


def get_file_size_mb(file_path: Path) -> float:
    """Retorna o tamanho do arquivo em MB."""
    return file_path.stat().st_size / (1024 * 1024)


def is_valid_upload(filename: str, max_size_mb: float = 50) -> tuple[bool, str]:
    """
    Verifica se o arquivo é válido para upload.

    Args:
        filename: Nome do arquivo
        max_size_mb: Tamanho máximo em MB

    Returns:
        Tupla (é_válido, mensagem_de_erro)
    """
    allowed_extensions = {'.pdf', '.txt', '.docx'}
    ext = Path(filename).suffix.lower()

    if ext not in allowed_extensions:
        return False, f"Tipo de arquivo não suportado. Use: {', '.join(allowed_extensions)}"

    return True, ""
