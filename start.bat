@echo off
setlocal
cd /d "%~dp0"
set "VENV=.venv"
if "%PORT%"=="" set "PORT=8000"

if not exist "%VENV%" (
  echo creating venv...
  python -m venv "%VENV%" || goto :error
)
call "%VENV%\Scripts\activate.bat" || goto :error

if exist requirements.txt (
  pip install -q -r requirements.txt || goto :error
) else (
  pip install -q pandas numpy networkx scikit-learn scipy pytest || goto :error
)

echo serving on http://localhost:%PORT%/sandbox/sandbox.html
start "" "http://localhost:%PORT%/sandbox/sandbox.html"
python -m http.server %PORT%
goto :eof

:error
echo failed. is python on your PATH?
exit /b 1
