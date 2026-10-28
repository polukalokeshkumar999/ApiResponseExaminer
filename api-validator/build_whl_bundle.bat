@echo off
setlocal

set WHL_DIR=whl
if not exist "%WHL_DIR%" mkdir "%WHL_DIR%"

REM Option A: Use your corporate mirror (recommended)
REM set PIP_INDEX_URL=https://<your-artifactory-or-internal-pypi>/simple
REM py -3.11 -m pip download -r requirements.txt -d "%WHL_DIR%" --index-url %PIP_INDEX_URL%

REM Option B: Public PyPI (works only if your network allows it)
py -3.11 -m pip download -r requirements.txt -d "%WHL_DIR%" --trusted-host pypi.org --trusted-host files.pythonhosted.org

if errorlevel 1 (
  echo.
  echo Wheel download failed. Use approved internal PyPI mirror or copy wheel files into %WHL_DIR% manually.
  exit /b 1
)

echo.
echo Wheel bundle created in %WHL_DIR%
endlocal
