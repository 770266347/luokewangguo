param(
    [ValidateSet("low", "medium", "high", "auto")]
    [string]$Quality = "medium",
    [string]$Size = "1024x1024",
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../../..")
$csvPath = Get-ChildItem -LiteralPath $PSScriptRoot -Filter "*.csv" |
    Where-Object { $_.Name -like "*13*.csv" } |
    Select-Object -First 1 -ExpandProperty FullName
$clientPath = Get-ChildItem -LiteralPath $repoRoot -Recurse -Filter "gpt_image2_client.py" |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $csvPath -or -not (Test-Path -LiteralPath $csvPath)) {
    throw "Missing 13-keyframe CSV in: $PSScriptRoot"
}

if (-not $clientPath -or -not (Test-Path -LiteralPath $clientPath)) {
    throw "Missing image2 client: $clientPath"
}

$keyNames = @("GPT_IMAGE2_API_KEY", "AICODE_API_KEY", "OPENAI_API_KEY")
$hasKey = $false
foreach ($name in $keyNames) {
    if ([Environment]::GetEnvironmentVariable($name)) {
        $hasKey = $true
        break
    }
}

if (-not $hasKey -and -not $DryRun) {
    throw "Missing API key. Set GPT_IMAGE2_API_KEY, AICODE_API_KEY, or OPENAI_API_KEY in this PowerShell session, then rerun this script."
}

$rows = Import-Csv -LiteralPath $csvPath -Encoding UTF8

foreach ($row in $rows) {
    $sourcePath = Join-Path (Split-Path $PSScriptRoot -Parent) $row.source_reference
    $outputPath = Join-Path (Split-Path $PSScriptRoot -Parent) $row.output_file

    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Missing source reference for $($row.clip_id): $sourcePath"
    }

    if ((Test-Path -LiteralPath $outputPath) -and -not $Force) {
        Write-Host "skip existing: $($row.output_file)"
        continue
    }

    $prompt = @"
Use the input image as the primary composition, character, scene, and felt stop-motion style reference.
Create this exact keyframe for a dialogue-driven short video.

Positive prompt:
$($row.positive_prompt)

Consistency rules:
- Keep the same handmade needle-felt stop-motion look as the input image.
- Keep the Roco Kingdom magical training field setting.
- Keep character proportions, colors, and felt texture stable.
- No readable text of any kind. Dialogue will be added later as subtitles and voiceover.

Avoid:
$($row.negative_prompt)
"@

    Write-Host "generate: $($row.clip_id) -> $($row.output_file)"

    $args = @(
        $clientPath,
        "edit",
        "--image", $sourcePath,
        "-p", $prompt,
        "-o", $outputPath,
        "--size", $Size,
        "--quality", $Quality,
        "--output-format", "png",
        "--session-id", "ai-comic-001-keyframes"
    )

    if ($DryRun) {
        $args += "--dry-run"
    }

    & py -3 @args

    if ($LASTEXITCODE -ne 0) {
        throw "image2 generation failed for $($row.clip_id)"
    }
}

Write-Host "done"
