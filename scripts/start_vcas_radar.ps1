param()

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "..")

$venv_python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$env:PYTHONPATH = (Get-Location).Path
$uvicorn_args = @("vcas.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info")

if (Test-Path $venv_python) {
  $python = $venv_python
  $python_args = @("-m", "uvicorn") + $uvicorn_args
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
  $python = "uv"
  $python_args = @("run", "-m", "uvicorn") + $uvicorn_args
} else {
  Write-Error "Could not find .venv\\Scripts\\python.exe or `uv` command."
  Write-Error "Run `uv sync` in this repo, then rerun this script."
  exit 1
}

Write-Host "Starting vCAS API on http://localhost:8000"
$outLog = Join-Path (Get-Location) "server8000.out.log"
$errLog = Join-Path (Get-Location) "server8000.err.log"
$process = Start-Process -FilePath $python -ArgumentList $python_args -WindowStyle Hidden -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog

$health_url = "http://127.0.0.1:8000/health"
for ($i = 0; $i -lt 30; $i += 1) {
  try {
    $null = Invoke-RestMethod -Uri $health_url -TimeoutSec 1
    break
  } catch {
    Start-Sleep -Milliseconds 400
  }
}

if ($process.HasExited) {
  Write-Error "vCAS launcher exited immediately."
  Write-Error "Check installed deps: uv sync."
  exit 1
}

Write-Host "API process started (pid=$($process.Id))."
Write-Host "Open Radar UI: http://localhost:8000/demo/radar.html"
if (Get-Command cmd -ErrorAction SilentlyContinue) {
  Start-Process "http://localhost:8000/demo/radar.html"
}
