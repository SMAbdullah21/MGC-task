$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (Select-String -LiteralPath ".env" -Pattern "your_gemini_api_key_here" -Quiet) {
    Write-Host "Replace the Gemini API placeholder in .env before starting." -ForegroundColor Yellow
    exit 1
}

python -m pip install -r requirements.txt
python web_app.py
