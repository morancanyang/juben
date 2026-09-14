# Keeps the competition Quick Tunnel connected to the local game server.
# The script is intentionally independent from the API process: if either the
# tunnel or the local server is restarted, the tunnel is recreated.
$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
if (-not (Test-Path -LiteralPath $Cloudflared)) {
    $Cloudflared = Join-Path $ProjectRoot 'tools\cloudflared.exe'
}
$Runtime = Join-Path $ProjectRoot 'runtime'
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
$UrlFile = Join-Path $Runtime 'cloudflared-url.txt'
$LogFile = Join-Path $Runtime 'cloudflared-watchdog.log'

function Write-Log([string]$Message) {
    Add-Content -LiteralPath $LogFile -Value ("{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
}

while ($true) {
    $runId = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $Runtime ("cloudflared-$runId.out.log")
    $stderr = Join-Path $Runtime ("cloudflared-$runId.err.log")
    Write-Log "starting cloudflared"
    $proc = Start-Process -FilePath $Cloudflared -ArgumentList @(
        'tunnel', '--no-autoupdate', '--protocol', 'http2', '--url', 'http://127.0.0.1:8765'
    ) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru

    # The quick tunnel URL is printed shortly after startup. Save it so the
    # current address can be found even when this watchdog is running hidden.
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $text = (((Get-Content -LiteralPath $stdout -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $stderr -ErrorAction SilentlyContinue)) -join "`n")
        $match = [regex]::Match($text, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) {
            Set-Content -LiteralPath $UrlFile -Value $match.Value -Encoding utf8
            Write-Log "tunnel url: $($match.Value)"
            break
        }
        if ($proc.HasExited) { break }
    }
    Wait-Process -Id $proc.Id -ErrorAction SilentlyContinue
    Write-Log "cloudflared exited; restarting in 3 seconds"
    Start-Sleep -Seconds 3
}
