@echo off
REM Script d'arrêt propre pour Orion (Windows)
cd /d "%~dp0"
python stop.py %*
if errorlevel 1 pause
