@echo off
:: Laris - Script de Instalacao para Windows

echo.
echo ========================================
echo   LARIS - Instalacao de Dependencias
echo ========================================
echo.

:: Backend
echo [1/4] Criando ambiente virtual Python...
cd backend
python -m venv venv
if errorlevel 1 (
    echo [ERRO] Falha ao criar ambiente virtual
    exit /b 1
)

echo [2/4] Instalando dependencias do backend...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias Python
    exit /b 1
)

:: Instala FFmpeg para pydub (necessario para concatenar audios longos)
echo [INFO] Verificando FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [AVISO] FFmpeg nao encontrado.
    echo Para textos longos, instale FFmpeg:
    echo   - Baixe de https://ffmpeg.org/download.html
    echo   - Ou use: winget install FFmpeg
    echo.
)

cd ..

:: Frontend
echo [3/4] Instalando dependencias do frontend...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias Node
    exit /b 1
)
cd ..

:: Cria diretorio outputs
echo [4/4] Criando diretorio de saida...
if not exist "outputs" mkdir outputs

echo.
echo ========================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo Para iniciar o Laris, execute: run.bat
echo.
