@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Smart Agric - Auto Connect Dashboard
pushd "%~dp0"
if errorlevel 1 goto folder_error

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto use_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto use_python

echo Python 3.10 or newer was not found.
echo Install it from https://www.python.org/downloads/windows/
echo Enable "Add Python to PATH" during installation, then run this file again.
popd
pause
exit /b 1

:use_py
py -3 "%~dp0start_local.py"
goto finished

:use_python
python "%~dp0start_local.py"
goto finished

:finished
set "START_RESULT=%ERRORLEVEL%"
echo.
echo Smart Agric has stopped. Keep this window open while using the dashboard.
popd
pause
exit /b %START_RESULT%

:folder_error
echo Could not open the dashboard folder. Extract the full ZIP before starting.
pause
exit /b 1
