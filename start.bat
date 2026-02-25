@echo off
chcp 65001 >nul 2>&1
title DKEC 工作進度追蹤系統

echo ==============================
echo  DKEC 工作進度追蹤系統
echo ==============================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3
    pause
    exit /b 1
)

:: Install Flask if needed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [安裝] 正在安裝 Flask...
    pip install flask
    echo.
)

echo [啟動] 正在啟動伺服器...
echo [開啟] http://localhost:5000
echo.
echo 按 Ctrl+C 可停止伺服器
echo.

:: Open browser after 2 seconds
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start Flask
python app.py
