@echo off
setlocal

set WHL_DIR=whl
if not exist "%WHL_DIR%" (
  echo whl folder not found. Create it and place wheel files first.
  exit /b 1
)

py -3.11 -m pip install --no-index --find-links "%WHL_DIR%" -r requirements.txt
if errorlevel 1 (
  echo.
  echo Offline install failed. Ensure all required wheels exist in %WHL_DIR%.
  exit /b 1
)

echo.
echo Dependencies installed successfully from %WHL_DIR%.
endlocal
