@echo off
setlocal

set WM_JAR=C:\wiremock\wiremock-standalone.jar
if not exist "%WM_JAR%" (
  echo WireMock standalone jar not found at %WM_JAR%
  exit /b 1
)

java -jar "%WM_JAR%" --port 9090 --root-dir wiremock

endlocal
