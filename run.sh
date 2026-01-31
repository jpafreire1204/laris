#!/bin/bash
# Laris - Script de Execução para macOS/Linux
# Execute: chmod +x run.sh && ./run.sh

set -e

echo ""
echo "========================================"
echo "       LARIS - Artigos em Áudio"
echo "========================================"
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não encontrado!"
    echo "Por favor, instale Python 3.11+"
    exit 1
fi

# Verifica Node
if ! command -v node &> /dev/null; then
    echo "[ERRO] Node.js não encontrado!"
    echo "Por favor, instale Node.js 18+"
    exit 1
fi

# Verifica se as dependências estão instaladas
if [ ! -d "backend/venv" ]; then
    echo "[INFO] Primeira execução detectada. Instalando dependências..."
    echo "Isso pode levar alguns minutos..."
    echo ""
    ./setup.sh
fi

# Inicia backend
echo "[INFO] Iniciando backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Aguarda backend iniciar
echo "[INFO] Aguardando backend iniciar..."
sleep 3

# Inicia frontend
echo "[INFO] Iniciando frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Aguarda frontend iniciar
sleep 3

echo ""
echo "========================================"
echo "    LARIS INICIADO COM SUCESSO!"
echo "========================================"
echo ""
echo "Acesse no navegador:"
echo ""
echo "  http://localhost:5173"
echo ""
echo "Para encerrar, pressione Ctrl+C"
echo ""
echo "========================================"
echo ""

# Abre o navegador (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5173
# Linux
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:5173 2>/dev/null || echo "Abra http://localhost:5173 no navegador"
fi

# Trap para limpar processos ao sair
cleanup() {
    echo ""
    echo "[INFO] Encerrando Laris..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Mantém o script rodando
wait
