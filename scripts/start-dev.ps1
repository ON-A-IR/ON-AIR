$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendUrl = "http://127.0.0.1:8000/api/health"
$FrontendUrl = "http://127.0.0.1:5173/"
$BackendOutLog = Join-Path $Root ".dev-backend.out.log"
$BackendErrLog = Join-Path $Root ".dev-backend.err.log"
$BackendProcess = $null

function Test-Url($Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  }
  catch {
    return $false
  }
}

function Get-ProjectPython {
  $candidates = @(
    (Join-Path $Root ".venv-win\Scripts\python.exe"),
    (Join-Path $Root ".venv\bin\python.exe"),
    (Join-Path $Root ".venv\Scripts\python.exe")
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  throw "Python 가상환경을 찾지 못했습니다. .venv를 먼저 만들어야 합니다."
}

try {
  Set-Location $Root

  if (Test-Url $BackendUrl) {
    Write-Host "[ON-AIR] Backend already running: http://127.0.0.1:8000"
  }
  else {
    $python = Get-ProjectPython
    Write-Host "[ON-AIR] Starting backend..."
    $BackendProcess = Start-Process `
      -FilePath $python `
      -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
      -WorkingDirectory $Root `
      -RedirectStandardOutput $BackendOutLog `
      -RedirectStandardError $BackendErrLog `
      -PassThru

    for ($i = 0; $i -lt 20; $i++) {
      if (Test-Url $BackendUrl) {
        break
      }
      Start-Sleep -Milliseconds 500
    }

    if (-not (Test-Url $BackendUrl)) {
      Write-Host "[ON-AIR] Backend failed to start."
      if (Test-Path $BackendErrLog) {
        Get-Content $BackendErrLog -Tail 20
      }
      exit 1
    }
  }

  if (Test-Url $FrontendUrl) {
    Write-Host "[ON-AIR] Frontend already running: $FrontendUrl"
    Write-Host "[ON-AIR] Open this URL in Chrome."
    exit 0
  }

  Write-Host "[ON-AIR] Starting frontend..."
  Write-Host "[ON-AIR] Open: $FrontendUrl"
  npm.cmd run dev:frontend
}
finally {
  if ($BackendProcess -and -not $BackendProcess.HasExited) {
    Write-Host "[ON-AIR] Stopping backend..."
    Stop-Process -Id $BackendProcess.Id -Force
  }
}
