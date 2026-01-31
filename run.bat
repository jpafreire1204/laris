@echo off
:: Laris - Script de Execucao para Windows
:: Execute este arquivo para iniciar o Laris

echo.
echo ========================================
echo        LARIS - Artigos em Audio
echo ========================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale Python 3.11+ de https://python.org
    pause
    exit /b 1
)

:: Verifica Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado!
    echo Por favor, instale Node.js 18+ de https://nodejs.org
    pause
    exit /b 1
)

:: Verifica se as dependencias estao instaladas
if not exist "backend\venv" (
    echo [INFO] Primeira execucao detectada. Instalando dependencias...
    echo Isso pode levar alguns minutos...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo [ERRO] Falha na instalacao
        pause
        exit /b 1
    )
)

echo [INFO] Iniciando backend...
cd backend
start "Laris Backend" cmd /c "venv\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
cd ..

:: Aguarda backend iniciar
echo [INFO] Aguardando backend iniciar...
timeout /t 3 /nobreak >nul

echo [INFO] Iniciando frontend...
cd frontend
start "Laris Frontend" cmd /c "npm run dev"
cd ..

:: Aguarda frontend iniciar
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo        LARIS INICIADO COM SUCESSO!
echo ========================================
echo.
echo Acesse no navegador:
echo.
echo   http://localhost:5173
echo.
echo Para encerrar, feche as janelas do terminal
echo ou pressione Ctrl+C em cada uma.
echo.
echo ========================================
echo.

:: Abre o navegador
start http://localhost:5173

pause
