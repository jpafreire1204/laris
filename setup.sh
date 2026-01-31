#!/bin/bash
# Laris - Script de Instalação para macOS/Linux
# Execute: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "========================================"
echo "  LARIS - Instalação de Dependências"
echo "========================================"
echo ""

# Backend
echo "[1/4] Criando ambiente virtual Python..."
cd backend
python3 -m venv venv
source venv/bin/activate

echo "[2/4] Instalando dependências do backend..."
pip install --upgrade pip
pip install -r requirements.txt

# Verifica FFmpeg
echo "[INFO] Verificando FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "[AVISO] FFmpeg não encontrado."
    echo "Para textos longos, instale FFmpeg:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install ffmpeg"
    else
        echo "  sudo apt install ffmpeg  (Debian/Ubuntu)"
        echo "  sudo dnf install ffmpeg  (Fedora)"
    fi
    echo ""
fi

cd ..

# Frontend
echo "[3/4] Instalando dependências do frontend..."
cd frontend
npm install
cd ..

# Cria diretório outputs
echo "[4/4] Criando diretório de saída..."
mkdir -p outputs

echo ""
echo "========================================"
echo "  INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "========================================"
echo ""
echo "Para iniciar o Laris, execute: ./run.sh"
echo ""
