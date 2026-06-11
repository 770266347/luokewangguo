param(
  [Parameter(Position = 0, Mandatory = $true)]
  [ValidateSet("create", "get", "poll", "download")]
  [string]$Command,

  [string]$ApiKey,
  [string]$BaseUrl = "https://apihub.agnes-ai.com/v1",
  [string]$Model = "agnes-video-v1.2",
  [string]$Prompt,
  [string]$ImageUrl,
  [string]$ImagePath,
  [string[]]$Images,
  [ValidateSet("ti2vid", "keyframes")]
  [string]$Mode = "ti2vid",
  [int]$Width = 1152,
  [int]$Height = 768,
  [int]$NumFrames = 121,
  [double]$FrameRate = 24,
  [int]$NumInferenceSteps = 0,
  [int]$Seed = 0,
  [string]$NegativePrompt,
  [string]$TaskId,
  [string]$Output = "agnes_video.mp4",
  [int]$PollIntervalSeconds = 10,
  [int]$TimeoutSeconds = 1200,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-AgnesApiKey {
  if ($ApiKey) { return $ApiKey }
  foreach ($name in @("AGNES_API_KEY", "AGNESAI_API_KEY", "AGNES_AI_API_KEY", "OPENAI_API_KEY")) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { return $value }
  }
  foreach ($envPath in @(
    (Join-Path $PSScriptRoot ".env"),
    (Join-Path (Get-Location) ".env")
  )) {
    if (Test-Path -LiteralPath $envPath) {
      foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match "^\s*(AGNES_API_KEY|AGNESAI_API_KEY|AGNES_AI_API_KEY|OPENAI_API_KEY)\s*=\s*(.+?)\s*$") {
          return $matches[2].Trim().Trim('"').Trim("'")
        }
      }
    }
  }
  throw "Missing API key. Set AGNES_API_KEY, or pass -ApiKey."
}

function Get-Headers {
  $key = Get-AgnesApiKey
  return @{
    "Authorization" = "Bearer $key"
    "Content-Type" = "application/json"
  }
}

function Assert-FrameCount {
  if ($NumFrames -gt 441) {
    throw "NumFrames must be <= 441."
  }
  if ((($NumFrames - 1) % 8) -ne 0) {
    throw "NumFrames must satisfy 8n + 1, for example 81, 121, 161, 241, 441."
  }
}

function Convert-ImagePathToDataUrl($Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "ImagePath not found: $Path"
  }
  $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
  $mime = switch ($extension) {
    ".png" { "image/png" }
    ".jpg" { "image/jpeg" }
    ".jpeg" { "image/jpeg" }
    ".webp" { "image/webp" }
    default { throw "Unsupported image type: $extension. Use PNG, JPEG, or WEBP." }
  }
  $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path))
  $b64 = [Convert]::ToBase64String($bytes)
  return "data:$mime;base64,$b64"
}

function ConvertTo-CleanJson($Object) {
  return ($Object | ConvertTo-Json -Depth 20)
}

function New-CreatePayload {
  if (-not $Prompt) { throw "Create requires -Prompt." }
  Assert-FrameCount

  $payload = [ordered]@{
    model = $Model
    prompt = $Prompt
    width = $Width
    height = $Height
    num_frames = $NumFrames
    frame_rate = $FrameRate
  }

  if ($ImageUrl -and $ImagePath) {
    throw "Use either -ImageUrl or -ImagePath, not both."
  }

  if ($ImagePath) {
    $payload.image = Convert-ImagePathToDataUrl $ImagePath
  } elseif ($ImageUrl) {
    $payload.image = $ImageUrl
  }

  if ($Mode -and $Mode -ne "ti2vid") {
    $payload.mode = $Mode
  }

  if ($NumInferenceSteps -gt 0) {
    $payload.num_inference_steps = $NumInferenceSteps
  }

  if ($Seed -ne 0) {
    $payload.seed = $Seed
  }

  if ($NegativePrompt) {
    $payload.negative_prompt = $NegativePrompt
  }

  if ($Images -and $Images.Count -gt 0) {
    $extra = [ordered]@{
      image = $Images
    }
    if ($Mode -eq "keyframes") {
      $extra.mode = "keyframes"
    }
    $payload.extra_body = $extra
  }

  return $payload
}

function Invoke-AgnesPost($Path, $Payload) {
  $uri = $BaseUrl.TrimEnd("/") + $Path
  $json = ConvertTo-CleanJson $Payload
  if ($DryRun) {
    Write-Output $json
    return
  }
  Invoke-RestMethod -Method Post -Uri $uri -Headers (Get-Headers) -Body $json
}

function Invoke-AgnesGet($Path) {
  $uri = $BaseUrl.TrimEnd("/") + $Path
  if ($DryRun) {
    Write-Output "GET $uri"
    return
  }
  Invoke-RestMethod -Method Get -Uri $uri -Headers (Get-Headers)
}

function Get-TaskIdFromResult($Result) {
  foreach ($name in @("id", "task_id", "video_id")) {
    if ($Result.PSObject.Properties.Name -contains $name) {
      $value = $Result.$name
      if ($value) { return $value }
    }
  }
  return $null
}

function Get-VideoUrlFromResult($Result) {
  foreach ($name in @("video_url", "url", "output_url")) {
    if ($Result.PSObject.Properties.Name -contains $name) {
      $value = $Result.$name
      if ($value) { return $value }
    }
  }
  if ($Result.PSObject.Properties.Name -contains "output" -and $Result.output) {
    foreach ($name in @("video_url", "url")) {
      if ($Result.output.PSObject.Properties.Name -contains $name) {
        $value = $Result.output.$name
        if ($value) { return $value }
      }
    }
  }
  return $null
}

function Show-Result($Result) {
  $Result | ConvertTo-Json -Depth 20
}

switch ($Command) {
  "create" {
    $payload = New-CreatePayload
    if ($DryRun) {
      ConvertTo-CleanJson $payload
      return
    }
    $result = Invoke-AgnesPost "/videos" $payload
    Show-Result $result
  }

  "get" {
    if (-not $TaskId) { throw "Get requires -TaskId." }
    $result = Invoke-AgnesGet "/videos/$TaskId"
    if (-not $DryRun) {
      Show-Result $result
    }
  }

  "poll" {
    if (-not $TaskId) { throw "Poll requires -TaskId." }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
      $result = Invoke-AgnesGet "/videos/$TaskId"
      if ($DryRun) { return }

      $status = $result.status
      $progress = $result.progress
      Write-Host "status=$status progress=$progress"

      if ($status -eq "completed") {
        Show-Result $result
        $videoUrl = Get-VideoUrlFromResult $result
        if ($videoUrl) {
          Write-Host "video_url=$videoUrl"
        }
        return
      }

      if ($status -eq "failed") {
        Show-Result $result
        throw "Agnes video task failed."
      }

      Start-Sleep -Seconds $PollIntervalSeconds
    } while ((Get-Date) -lt $deadline)

    throw "Polling timed out after $TimeoutSeconds seconds."
  }

  "download" {
    if (-not $TaskId) { throw "Download requires -TaskId." }
    $result = Invoke-AgnesGet "/videos/$TaskId"
    if ($DryRun) { return }

    $videoUrl = Get-VideoUrlFromResult $result
    if (-not $videoUrl) {
      Show-Result $result
      throw "No video_url found. Task may not be completed."
    }

    $outputParent = Split-Path -Parent $Output
    if ($outputParent -and -not (Test-Path -LiteralPath $outputParent)) {
      New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
    }
    Invoke-WebRequest -Uri $videoUrl -OutFile $Output
    Write-Output "saved: $Output"
  }
}
