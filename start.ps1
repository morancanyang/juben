param([int]$ApiPort = 8000, [int]$WebPort = 5173)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Missing .venv. Run: python -m venv .venv; .venv/Scripts/pip install -r api/requirements.txt' }
& .venv/Scripts/python.exe -m api.migrate
$api = Start-Process -FilePath (Join-Path $PWD '.venv/Scripts/python.exe') -ArgumentList '-m','uvicorn','api.main:app','--host','127.0.0.1','--port',"$ApiPort" -PassThru -WindowStyle Hidden
try {
  Write-Host "API: http://127.0.0.1:$ApiPort"
  Set-Location web
  Write-Host "Web: http://127.0.0.1:$WebPort"
  npm run dev -- --port $WebPort
} finally { if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force } }
