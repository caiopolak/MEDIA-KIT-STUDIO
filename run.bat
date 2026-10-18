@echo off
title NEXUS DOWNLOADER • System Boot
chcp 65001 >nul

:: ===========================
::   INTERFACE VISUAL
:: ===========================
cls
echo.
echo    ╔══════════════════════════════════════════╗
echo    ║            ⬇ NEXUS DOWNLOADER ⬇          ║
echo    ╚══════════════════════════════════════════╝
echo.
echo        Preparando ambiente... Aguarde.
echo.

:: ===========================
::   CHECANDO PYTHON
:: ===========================
echo ► Verificando dependências do Python...
python --version >nul 2>&1

if errorlevel 1 (
    echo ❌ Python não encontrado!
    echo    Instale Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

echo ✔ Python detectado!
echo.

:: ===========================
::   INSTALANDO REQUIREMENTS
:: ===========================
echo ► Instalando/atualizando dependências...
pip install -r requirements.txt
echo.

:: ===========================
::      INICIANDO APP
:: ===========================
echo ► Iniciando Nexus Downloader...
echo.
python main.py

echo.
echo ════════════════════════════════════════════════
echo   Execução concluída. Pressione qualquer tecla.
echo ════════════════════════════════════════════════
pause >nul
