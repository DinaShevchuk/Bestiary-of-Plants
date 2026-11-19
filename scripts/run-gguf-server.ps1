param(
    [ValidateSet('kunoichi', 'tiefighter')]
    [string]$Model = 'kunoichi',
    [int]$Port = 8080,
    [int]$ContextSize = 4096,
    [int]$GpuLayers = 0
)

$ErrorActionPreference = 'Stop'
$modelsDirectory = Join-Path $env:APPDATA 'faraday\models'
if (-not (Test-Path -LiteralPath $modelsDirectory -PathType Container)) {
    throw "Faraday models directory not found: $modelsDirectory"
}

$prefix = switch ($Model) {
    'kunoichi' { 'mistral.7b.kunoichi.gguf_v2.q4_k_m' }
    'tiefighter' { 'llama2.13b.tiefighter.gguf_v2.q4_k_m' }
}
$matches = @(Get-ChildItem -LiteralPath $modelsDirectory -File | Where-Object { $_.Name -like "$prefix*" })
if ($matches.Count -eq 0) {
    $visible = (Get-ChildItem -LiteralPath $modelsDirectory -File | Select-Object -ExpandProperty Name) -join "`n"
    throw "No model file matched '$prefix*'. Files in directory:`n$visible"
}
if ($matches.Count -gt 1) {
    $choices = ($matches | Select-Object -ExpandProperty Name) -join "`n"
    throw "Several files matched '$prefix*'. Please keep one exact variant or specify it manually:`n$choices"
}

$server = Get-Command 'llama-server.exe' -ErrorAction SilentlyContinue
if (-not $server) {
    $server = Get-Command 'llama-server' -ErrorAction SilentlyContinue
}
if (-not $server) {
    throw "llama-server was not found in PATH. Install llama.cpp (winget install -e --id ggml.llamacpp) and open a new PowerShell window."
}

$alias = "bestiary-$Model"
Write-Host "Loading $($matches[0].FullName)" -ForegroundColor Cyan
Write-Host "OpenAI-compatible endpoint: http://127.0.0.1:$Port/v1" -ForegroundColor Green
& $server.Source -m $matches[0].FullName --alias $alias --host 127.0.0.1 --port $Port --ctx-size $ContextSize --n-gpu-layers $GpuLayers
