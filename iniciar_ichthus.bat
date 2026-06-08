@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente .venv nao encontrado.
    echo Execute: py -3.12 -m venv .venv
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
