@echo off
chcp 65001 > nul
echo ===================================================
echo     Institute Django - Setup and Run Script
echo ===================================================
echo.

:: Checking Python installation
echo [1] Checking Python installation...
python --version
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo [OK] Python found.
echo.

:: Setting up Virtual Environment
echo [2] Setting up Virtual Environment...
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo Creating new virtual environment...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) ELSE (
    echo [OK] Virtual environment already exists.
)
echo.

:: Activating Virtual Environment
echo [3] Activating Virtual Environment...
call venv\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment activated.
echo.

:: Installing dependencies from requirements.txt
echo [4] Installing dependencies from requirements.txt...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

:: Running database migrations
echo [5] Running database migrations...
python manage.py migrate
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Database migration failed.
    echo.
    pause
    exit /b 1
)
echo [OK] Migrations applied.
echo.

:: Populating default users
IF EXIST "populate_users.py" (
    echo [6] Populating default users...
    python populate_users.py
    echo.
)

:: Server is starting
echo ===================================================
echo  Server is starting...
echo  Open your browser at: http://127.0.0.1:8000/
echo  Press CTRL+C to stop the server.
echo ===================================================
echo.
python manage.py runserver

echo.
echo Server has been stopped.
pause
