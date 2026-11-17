@echo off
REM Task 7 - install on a Windows machine with NO internet access.
REM Prerequisites: this whole folder incl. wheels\ (from scripts\package_offline.sh
REM run earlier on an online machine), Ollama installed, and the Ollama model
REM folder copied over with llama3.2:3b and nomic-embed-text already pulled.

echo == Installing Python dependencies from local wheels (no network) ==
python -m pip install --no-index --find-links wheels -r requirements.txt

echo == Disabling telemetry ==
set ANONYMIZED_TELEMETRY=False
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
(
  echo [browser]
  echo gatherUsageStats = false
) > "%USERPROFILE%\.streamlit\config.toml"

echo == Checking Ollama ==
where ollama >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  ollama --version
) else (
  echo WARNING: 'ollama' not found on PATH. Install it first using the
  echo offline installer obtained on an online machine from https://ollama.com/download
)

echo == Ingesting documents and building the search index ==
python src\ingest.py --rebuild
python src\search_index.py --build

echo.
echo Install complete. Try it:
echo   python src\ask.py "What is the vibration test duration for RADAR-100?"
echo   streamlit run ui\app.py
