@echo off
cd /d "%~dp0"
title Filtro de Promocoes - Telegram Bot

echo ======================================================
echo    INICIANDO BOT DE FILTRO DE PROMOCOES TELEGRAM
echo ======================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Criando ambiente virtual Python...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual. Verifique se o Python esta instalado.
        pause
        exit /b 1
    )
)

echo [2/3] Verificando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [3/3] Iniciando o bot...
echo.
python main.py

echo.
echo ======================================================
echo Bot finalizado.
pause
