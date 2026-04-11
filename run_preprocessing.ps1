param(
    [Parameter(Position = 0)]
    [string]$InputPath = ".\\CVs",

    [string]$OutputDir = ".\\output",

    [string]$Model = "gemini-2.5-flash",

    [switch]$Overwrite
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonPath = Join-Path $scriptDir ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

$cmdArgs = @(".\\preprocessing_script.py", $InputPath, "--output-dir", $OutputDir, "--model", $Model)
if ($Overwrite) {
    $cmdArgs += "--overwrite"
}

& $pythonPath @cmdArgs
exit $LASTEXITCODE
