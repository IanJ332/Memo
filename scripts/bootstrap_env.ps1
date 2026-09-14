# scripts/bootstrap_env.ps1
# Strictly repository-local Python virtual environment bootstrap for Windows.
# Does NOT modify global Python, execution policy, system environment, or PowerShell profiles.

$ErrorActionPreference = "Stop"

# Determine repository root relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

Set-Location -LiteralPath $RepoRoot

Write-Host "=== Bootstrapping Local Python Environment (Windows) ==="
Write-Host "Repository root: $RepoRoot"

# Discover Python interpreter safely
$PythonCmd = $null
$PyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
$PythonExe = Get-Command "python" -ErrorAction SilentlyContinue

if ($PyLauncher) {
    try {
        $testVer = & py -3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = @("py", "-3")
            Write-Host "Detected Python launcher: py -3 ($testVer)"
        }
    } catch {
        # py -3 not available
    }
}

if (-not $PythonCmd -and $PythonExe) {
    try {
        $testVer = & python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = @("python")
            Write-Host "Detected Python executable: python ($testVer)"
        }
    } catch {
        # python not available
    }
}

if (-not $PythonCmd) {
    Write-Error "ERROR: Python 3 was not found on PATH via 'py -3' or 'python'."
    Write-Error "Please install Python 3.10+ on Windows and ensure it is available on your PATH."
    exit 1
}

$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvDir)) {
    Write-Host "Creating repository-local virtual environment at: $VenvDir"
    if ($PythonCmd.Length -eq 2) {
        & $PythonCmd[0] $PythonCmd[1] -m venv $VenvDir
    } else {
        & $PythonCmd[0] -m venv $VenvDir
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPython)) {
        Write-Error "ERROR: Failed to create virtual environment at $VenvDir."
        exit 1
    }
} else {
    Write-Host "Existing virtual environment found at: $VenvDir"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Error "ERROR: Virtual environment interpreter not found at $VenvPython."
    exit 1
}

$VenvVer = & $VenvPython --version 2>&1
Write-Host "Using virtual environment interpreter: $VenvPython ($VenvVer)"

Write-Host "Upgrading pip inside .venv..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: Failed to upgrade pip in virtual environment."
    exit 1
}

$ReqFile = Join-Path $RepoRoot "requirements.txt"
if (Test-Path -LiteralPath $ReqFile) {
    Write-Host "Installing requirements inside .venv from $ReqFile..."
    & $VenvPython -m pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ERROR: Failed to install requirements in virtual environment."
        exit 1
    }
} else {
    Write-Warning "requirements.txt not found at $ReqFile"
}

Write-Host ""
Write-Host "Environment ready."
Write-Host "Python: $VenvPython"
Write-Host "Next command: $VenvPython scripts\system_probe.py"
