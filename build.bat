@echo off
title NEXUS MEDIA STUDIO - Build Tool
chcp 65001 >nul

:: ============================================
::   NEXUS MEDIA STUDIO - BUILD AUTOMATIZADA
:: ============================================
cls
echo.
echo    ╔══════════════════════════════════════════╗
echo    ║     🔨 NEXUS MEDIA STUDIO - BUILD TOOL    ║
echo    ╚══════════════════════════════════════════╝
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado!
    pause
    exit /b 1
)

:: Verifica se o ícone existe
if exist icon.ico (
    echo 🎨 Ícone encontrado: icon.ico
) else (
    echo ⚠️  Arquivo icon.ico não encontrado!
    echo    O executável será gerado sem ícone.
)

:: Executa build
python build_exe.py

echo.
echo    ════════════════════════════════════════════
echo      Build concluída! Pressione qualquer tecla
echo    ════════════════════════════════════════════
pause >nul