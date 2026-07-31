@echo off
:: Pure ASCII batch file to avoid CMD UTF-8 parsing bugs

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

pushd "%~dp0"
color 0A
title [ Institute Management System ]
cls

echo ========================================================
echo        Institute Management System - Startup
echo ========================================================
echo.

echo [1/5] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found!
    goto :FAIL
)

echo [2/5] Virtual Environment...
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 goto :FAIL
)

echo [3/5] Installing Dependencies...
"venv\Scripts\python.exe" -c "import django" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    "venv\Scripts\pip.exe" install -r requirements.txt --quiet
    if %ERRORLEVEL% NEQ 0 goto :FAIL
)

echo [4/5] Starting MariaDB Service...
sc query MariaDB | find "RUNNING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    net start MariaDB >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to start MariaDB service.
        goto :FAIL
    )
    timeout /t 3 /nobreak >nul
)

echo [5/5] Migrating Database...
"venv\Scripts\python.exe" manage.py migrate --verbosity 0 >nul 2>&1

title [ Institute Management System - RUNNING ]
cls
echo ========================================================
echo.
echo    SYSTEM IS RUNNING SUCCESSFULLY!
echo.
echo    Open your browser and go to:
echo          http://127.0.0.1:8000
echo.
echo    Press Ctrl+C to stop the server.
echo.
echo ========================================================
echo.

"venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000

echo.
echo Server Stopped.
popd
pause
exit /b

:FAIL
echo.
echo [!] SYSTEM STARTUP FAILED.
popd
pause
exit /b 1
