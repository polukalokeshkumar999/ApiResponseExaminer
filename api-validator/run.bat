@echo off
setlocal

if not exist .venv (
  py -3.11 -m venv .venv
)

call .venv\Scripts\activate
pip install -r requirements.txt
python main.py --config config.yaml

endlocal
