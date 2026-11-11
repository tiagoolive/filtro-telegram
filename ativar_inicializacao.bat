@echo off
cd /d "%~dp0"
title Ativar Inicializacao Automatica - Filtro Telegram

echo ==============================================================
echo    CONFIGURANDO INICIALIZACAO AUTOMATICA NO WINDOWS
echo ==============================================================
echo.

if not exist "venv\Scripts\pythonw.exe" (
    echo [ERRO] Ambiente virtual nao encontrado. Execute iniciar.bat primeiro.
    pause
    exit /b 1
)

if not exist "filtro_promocoes.session" (
    echo [AVISO] Voce ainda nao fez o primeiro login!
    echo Execute iniciar.bat ao menos uma vez antes para conectar sua conta.
    echo.
)

set "PROJ_DIR=%~dp0"
if "%PROJ_DIR:~-1%"=="\" set "PROJ_DIR=%PROJ_DIR:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$startup = [Environment]::GetFolderPath('Startup'); " ^
    "$lnk = $ws.CreateShortcut((Join-Path $startup 'FiltroTelegram.lnk')); " ^
    "$lnk.TargetPath = '%PROJ_DIR%\venv\Scripts\pythonw.exe'; " ^
    "$lnk.Arguments = 'main.py'; " ^
    "$lnk.WorkingDirectory = '%PROJ_DIR%'; " ^
    "$lnk.Description = 'Bot de Filtro de Promocoes Telegram'; " ^
    "$lnk.Save()"

if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar o atalho de inicializacao.
    pause
    exit /b 1
)

echo [OK] Atalho criado com sucesso na pasta Inicializar do Windows!
echo      O bot sera iniciado automaticamente em segundo plano (sem janela aberta)
echo      toda vez que voce ligar o PC.
echo.
echo      - Logs de execucao ficam salvos em: bot.log
echo      - Para desativar no futuro, execute: desativar_inicializacao.bat
echo.
pause

