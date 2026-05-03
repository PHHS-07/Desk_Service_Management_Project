Param(
    [int]$Port = 8000
)

# Activate virtualenv if present
$venvActivate = Join-Path $PSScriptRoot '..\venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    & $venvActivate
}

Write-Output "Checking for process using port $Port..."
try {
    $tcp = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
} catch {
    $tcp = $null
}
if ($tcp) {
    $pids = $tcp | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        Write-Output "Killing process $pid on port $Port"
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "No process found on port $Port."
}

Write-Output "Starting Django development server on port $Port..."
python manage.py runserver 0.0.0.0:$Port
