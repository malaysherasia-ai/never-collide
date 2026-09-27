@echo off
rem never-collide CLI wrapper for cmd.exe and PowerShell, where the Python
rem script next to this file cannot be run directly.
setlocal
set "NCL=%~dp0ncl"
if defined NCL_PYTHON ( "%NCL_PYTHON%" "%NCL%" %* & exit /b %errorlevel% )
python -c "import sys" >nul 2>&1 && ( python "%NCL%" %* & exit /b %errorlevel% )
py -c "import sys" >nul 2>&1 && ( py "%NCL%" %* & exit /b %errorlevel% )
echo never-collide: no working python found 1>&2
exit /b 1
