$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example." -ForegroundColor Yellow
    Write-Host "Open .env, replace your_gemini_api_key_here with a valid key, then run this script again."
    exit 1
}

if (Select-String -LiteralPath ".env" -Pattern "your_gemini_api_key_here" -Quiet) {
    Write-Host "Add a valid GEMINI_API_KEY to .env before starting." -ForegroundColor Yellow
    exit 1
}

python -m pip install -r requirements.txt
python web_app.py
