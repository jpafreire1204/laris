"""
Laris - Backend Principal
Aplicação FastAPI para conversão de artigos científicos em áudio.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import extract_router, translate_router, tts_router, voices_router
from app.utils.file_utils import ensure_outputs_dir, cleanup_old_files

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    logger.info("Iniciando Laris...")
    ensure_outputs_dir()
    cleanup_old_files(max_age_hours=24)
    logger.info("Laris iniciado com sucesso!")

    yield

    # Shutdown
    logger.info("Encerrando Laris...")


# Cria aplicação FastAPI
app = FastAPI(
    title="Laris",
    description=(
        "API para conversão de artigos científicos em áudio. "
        "Extrai texto de PDFs, traduz para português e gera narração."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Configuração CORS (permite frontend local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Next.js
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra rotas
app.include_router(extract_router, prefix="/api", tags=["Extração"])
app.include_router(translate_router, prefix="/api", tags=["Tradução"])
app.include_router(tts_router, prefix="/api", tags=["TTS"])
app.include_router(voices_router, prefix="/api", tags=["Vozes"])


@app.get("/")
async def root():
    """Rota raiz - verifica se API está funcionando."""
    return {
        "name": "Laris",
        "version": "1.0.0",
        "status": "online",
        "description": "Conversor de artigos científicos em áudio"
    }


@app.get("/health")
async def health():
    """Verifica saúde da API."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
