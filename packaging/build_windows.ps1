param(
    [ValidateSet("all", "host", "client", "viewer")]
    [string]$Target = "all",
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$TempBuildRoot = Join-Path ([System.IO.Path]::GetTempPath()) "ailatrieuphu-pyinstaller"
$TempDist = Join-Path $TempBuildRoot "dist"
$TempWork = Join-Path $TempBuildRoot "work"
$TempSpecs = Join-Path $TempBuildRoot "specs"
$RepoDist = Join-Path $RepoRoot "dist"

if (Test-Path $TempBuildRoot) {
    Remove-Item -LiteralPath $TempBuildRoot -Recurse -Force
}
if (Test-Path $RepoDist) {
    Remove-Item -LiteralPath $RepoDist -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $TempDist, $TempWork, $TempSpecs, $RepoDist | Out-Null

$env:AILTP_PYI_DIST_DIR = $TempDist
$env:AILTP_PYI_BUILD_DIR = $TempWork
$env:AILTP_PYI_SPEC_DIR = $TempSpecs

function Resolve-Python {
    $Candidates = @()

    if ($env:AILTP_PYTHON) {
        $Candidates += @{ Command = $env:AILTP_PYTHON; Args = @() }
    }

    $CodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $CodexPython) {
        $Candidates += @{ Command = $CodexPython; Args = @() }
    }

    $Candidates += @{ Command = "python"; Args = @() }
    $Candidates += @{ Command = "python3"; Args = @() }
    $Candidates += @{ Command = "py"; Args = @("-3.12") }
    $Candidates += @{ Command = "py"; Args = @("-3") }

    foreach ($Candidate in $Candidates) {
        $Command = Get-Command $Candidate.Command -ErrorAction SilentlyContinue
        if (-not $Command -and -not (Test-Path $Candidate.Command)) {
            continue
        }

        try {
            $Output = @(& $Candidate.Command @($Candidate.Args) -c "import sys; print(sys.executable)" 2>$null)
            if ($LASTEXITCODE -eq 0 -and $Output.Count -gt 0) {
                return @{
                    Command = $Candidate.Command
                    Args = $Candidate.Args
                    Display = $Output[$Output.Count - 1]
                }
            }
        } catch {
            continue
        }
    }

    throw "Could not find a working Python 3. Install Python 3.10+ or set AILTP_PYTHON to python.exe."
}

$Python = Resolve-Python
Write-Host "Using Python: $($Python.Display)"

function Invoke-Python {
    param(
        [string[]]$Arguments,
        [switch]$Optional
    )

    & $Python.Command @($Python.Args) @Arguments
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) {
            Write-Warning "Optional Python command failed: $($Arguments -join ' ')"
            return $false
        }
        throw "Python command failed: $($Arguments -join ' ')"
    }
    return $true
}

$null = Invoke-Python @("-m", "pip", "install", "Pillow>=10.0")
$null = Invoke-Python @("-m", "pip", "install", "pygame>=2.5") -Optional
$null = Invoke-Python @("-m", "pip", "install", "-r", "requirements-build.txt")

$BuildArgs = @("packaging/build_apps.py", "--target", $Target)
if ($OneFile) {
    $BuildArgs += "--onefile"
}

$null = Invoke-Python $BuildArgs

Copy-Item -Path (Join-Path $TempDist "*") -Destination $RepoDist -Recurse -Force
Write-Host "Output copied to: $RepoDist"
