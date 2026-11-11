@echo off
cd /d "%~dp0"
title Desativar Inicializacao Automatica - Filtro Telegram

echo ==============================================================
echo    REMOVENDO INICIALIZACAO AUTOMATICA NO WINDOWS
echo ==============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$startup = [Environment]::GetFolderPath('Startup'); " ^
    "$lnk = Join-Path $startup 'FiltroTelegram.lnk'; " ^
    "if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host '[OK] Atalho removido com sucesso!' -ForegroundColor Green } else { Write-Host '[INFO] O bot nao estava configurado para iniciar com o Windows.' -ForegroundColor Yellow }"

echo.
pause

