param(
    [string]$DataPath = "E:\luokewangguo\roco_world_data\data\roco_world_spirits.json",
    [ValidateSet("speed", "stats_total", "physical_attack", "magic_attack", "physical_defense", "magic_defense", "hp")]
    [string]$Metric = "physical_attack",
    [int]$TopN = 100,
    [string]$ImageCacheDir = "",
    [string]$OutputDir = "E:\luokewangguo\AI漫剧\排行榜",
    [string]$OutputName = "",
    [ValidateSet("standard", "phone_safe")]
    [string]$Layout = "standard"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Add-Type -AssemblyName System.Drawing

$metricInfo = @{
    speed = @{
        Label = "速度种族值"
        Title = "洛克王国：世界 速度种族值 TOP {0}"
        Subtitle = "按速度种族值降序排列；同值按种族值总和、编号排序"
        Csv = "洛克王国世界_速度种族值TOP{0}.csv"
        Png = "洛克王国世界_速度种族值TOP{0}.png"
        Cache = "speed_top{0}"
    }
    stats_total = @{
        Label = "种族值总和"
        Title = "洛克王国：世界 种族值 TOP {0}"
        Subtitle = "按种族值总和降序排列；同总和按速度、编号排序"
        Csv = "洛克王国世界_种族值TOP{0}.csv"
        Png = "洛克王国世界_种族值TOP{0}.png"
        Cache = "stats_total_top{0}"
    }
    physical_attack = @{
        Label = "物攻种族值"
        Title = "洛克王国：世界 物攻种族值 TOP {0}"
        Subtitle = "按物攻种族值降序排列；同值按种族值总和、速度、编号排序"
        Csv = "洛克王国世界_物攻种族值TOP{0}.csv"
        Png = "洛克王国世界_物攻种族值TOP{0}.png"
        Cache = "physical_attack_top{0}"
    }
    magic_attack = @{
        Label = "法攻种族值"
        Title = "洛克王国：世界 法攻种族值 TOP {0}"
        Subtitle = "按法攻种族值降序排列；同值按种族值总和、速度、编号排序"
        Csv = "洛克王国世界_法攻种族值TOP{0}.csv"
        Png = "洛克王国世界_法攻种族值TOP{0}.png"
        Cache = "magic_attack_top{0}"
    }
    physical_defense = @{
        Label = "物防种族值"
        Title = "洛克王国：世界 物防种族值 TOP {0}"
        Subtitle = "按物防种族值降序排列；同值按种族值总和、速度、编号排序"
        Csv = "洛克王国世界_物防种族值TOP{0}.csv"
        Png = "洛克王国世界_物防种族值TOP{0}.png"
        Cache = "physical_defense_top{0}"
    }
    magic_defense = @{
        Label = "魔防种族值"
        Title = "洛克王国：世界 魔防种族值 TOP {0}"
        Subtitle = "按魔防种族值降序排列；同值按种族值总和、速度、编号排序"
        Csv = "洛克王国世界_魔防种族值TOP{0}.csv"
        Png = "洛克王国世界_魔防种族值TOP{0}.png"
        Cache = "magic_defense_top{0}"
    }
    hp = @{
        Label = "精力种族值"
        Title = "洛克王国：世界 精力种族值 TOP {0}"
        Subtitle = "按精力种族值降序排列；同值按种族值总和、速度、编号排序"
        Csv = "洛克王国世界_精力种族值TOP{0}.csv"
        Png = "洛克王国世界_精力种族值TOP{0}.png"
        Cache = "hp_top{0}"
    }
}

$info = $metricInfo[$Metric]
$metricLabel = $info.Label
$metricTitle = $info.Title -f $TopN
$metricSubtitle = $info.Subtitle
$csvName = $info.Csv -f $TopN
if (-not $OutputName) { $OutputName = $info.Png -f $TopN }
if (-not $ImageCacheDir) {
    $ImageCacheDir = Join-Path "E:\luokewangguo\roco_world_data\assets\spirits" ($info.Cache -f $TopN)
}

New-Item -ItemType Directory -Force -Path $ImageCacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$assetRoot = "E:\luokewangguo\roco_world_data\assets\spirits"
$allSpiritImages = @()
if (Test-Path -LiteralPath $assetRoot) {
    $allSpiritImages = Get-ChildItem -LiteralPath $assetRoot -Recurse -File |
        Where-Object {
            $_.Extension -in @(".png", ".jpg", ".jpeg", ".webp") -and
            $_.FullName -notlike "$ImageCacheDir*"
        }
}

function To-Int($value, $fallback = 0) {
    $out = 0
    if ([int]::TryParse([string]$value, [ref]$out)) { return $out }
    return $fallback
}

function Safe-FileName($text) {
    $invalid = [IO.Path]::GetInvalidFileNameChars()
    $chars = ([string]$text).ToCharArray() | ForEach-Object {
        if ($invalid -contains $_) { "_" } else { $_ }
    }
    return -join $chars
}

function Download-Image($url, $path) {
    if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Length -gt 1024)) {
        return
    }
    if (-not $url) { return }

    $tmpPath = "$path.download"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmpPath -TimeoutSec 60 -Headers @{ "User-Agent" = "Mozilla/5.0" }
        Move-Item -LiteralPath $tmpPath -Destination $path -Force
    }
    finally {
        if (Test-Path -LiteralPath $tmpPath) {
            Remove-Item -LiteralPath $tmpPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Find-CachedImage($number, $name) {
    $num = [string]$number
    $display = [string]$name
    $match = $allSpiritImages |
        Where-Object { $_.Name -like "*_${num}_*" -and $_.BaseName -like "*$display*" } |
        Select-Object -First 1
    if ($match) { return $match.FullName }

    $match = $allSpiritImages |
        Where-Object { $_.Name -like "*_${num}_*" } |
        Select-Object -First 1
    if ($match) { return $match.FullName }

    $match = $allSpiritImages |
        Where-Object { $_.BaseName -like "*$display*" } |
        Select-Object -First 1
    if ($match) { return $match.FullName }

    return $null
}

function New-Font($size, [System.Drawing.FontStyle]$style = [System.Drawing.FontStyle]::Regular) {
    $families = @("Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Arial")
    foreach ($family in $families) {
        try {
            $font = New-Object System.Drawing.Font($family, $size, $style, [System.Drawing.GraphicsUnit]::Pixel)
            if ($font.Name -eq $family -or $font.FontFamily.Name -eq $family) { return $font }
            $font.Dispose()
        } catch {
        }
    }
    return New-Object System.Drawing.Font("Arial", $size, $style, [System.Drawing.GraphicsUnit]::Pixel)
}

function Fit-Font($graphics, $text, $baseSize, $minSize, $maxWidth, [System.Drawing.FontStyle]$style = [System.Drawing.FontStyle]::Regular) {
    for ($size = $baseSize; $size -ge $minSize; $size -= 2) {
        $font = New-Font $size $style
        $measured = $graphics.MeasureString($text, $font)
        if ($measured.Width -le $maxWidth) { return $font }
        $font.Dispose()
    }
    return New-Font $minSize $style
}

function Fill-RoundedRectangle($graphics, $brush, $x, $y, $w, $h, $r) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $r * 2
    $path.AddArc($x, $y, $d, $d, 180, 90)
    $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    $graphics.FillPath($brush, $path)
    $path.Dispose()
}

function Draw-CenteredText($graphics, $text, $font, $brush, $rect) {
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoWrap
    $graphics.DrawString($text, $font, $brush, $rect, $format)
    $format.Dispose()
}

$json = Get-Content -LiteralPath $DataPath -Raw -Encoding UTF8 | ConvertFrom-Json
$ranked = $json |
    Where-Object { $_.$Metric -ne $null -and $_.$Metric -ne "" } |
    Sort-Object `
        @{ Expression = { -(To-Int $_.$Metric) } }, `
        @{ Expression = { -(To-Int $_.stats_total) } }, `
        @{ Expression = { -(To-Int $_.speed) } }, `
        @{ Expression = { To-Int $_.number 9999 } }, `
        @{ Expression = { if ($_.display_name) { [string]$_.display_name } else { [string]$_.name } } } |
    Select-Object -First $TopN

$csvPath = Join-Path $OutputDir $csvName
$ranked | ForEach-Object -Begin { $i = 0 } -Process {
    $i++
    $record = [ordered]@{
        rank = $i
        number = $_.number
        name = if ($_.display_name) { $_.display_name } else { $_.name }
    }
    $record[$Metric] = $_.$Metric
    $record["stats_total"] = $_.stats_total
    $record["hp"] = $_.hp
    $record["physical_attack"] = $_.physical_attack
    $record["magic_attack"] = $_.magic_attack
    $record["physical_defense"] = $_.physical_defense
    $record["magic_defense"] = $_.magic_defense
    $record["speed"] = $_.speed
    $record["image_url"] = $_.image_url
    $record["source_url"] = $_.source_url
    [PSCustomObject]$record
} | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$phoneSafe = $Layout -eq "phone_safe"
$width = if ($phoneSafe) { 1080 } else { 1200 }
$headerH = 250
$rowH = 148
$footerH = 80
$height = $headerH + $ranked.Count * $rowH + $footerH

if ($phoneSafe) {
    $safeL = 88
    $safeR = 88
    $rankX = 96
    $imageX = 176
    $nameX = 318
    $nameMaxW = 300
    $barX = 662
    $barW = 158
    $metricRight = $width - $safeR
    $titleX = $safeL
    $subtitleX = $safeL + 2
    $lineL = $safeL
    $lineR = $width - $safeR
    $headerRankX = $rankX + 6
    $headerImageX = $imageX + 10
    $headerNameX = $nameX
    $headerMetricX = $barX + 122
    $footerX = $safeL
} else {
    $safeL = 54
    $safeR = 54
    $rankX = 58
    $imageX = 160
    $nameX = 336
    $nameMaxW = 355
    $barX = 720
    $barW = 250
    $metricRight = $width - 98
    $titleX = 54
    $subtitleX = 58
    $lineL = 48
    $lineR = $width - 48
    $headerRankX = 64
    $headerImageX = 178
    $headerNameX = 338
    $headerMetricX = 915
    $footerX = 54
}

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$graphics.Clear([System.Drawing.Color]::FromArgb(247, 250, 253))

$titleFont = New-Font 54 ([System.Drawing.FontStyle]::Bold)
$subtitleFont = New-Font 24
$headerFont = New-Font 22 ([System.Drawing.FontStyle]::Bold)
$rankFont = New-Font 26 ([System.Drawing.FontStyle]::Bold)
$metricFont = New-Font 42 ([System.Drawing.FontStyle]::Bold)
$smallFont = New-Font 18

$dark = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(24, 35, 48))
$muted = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(100, 116, 139))
$white = [System.Drawing.Brushes]::White
$blue = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(30, 100, 210))
$linePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(224, 231, 240), 2)

$headerBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    (New-Object System.Drawing.Rectangle(0, 0, $width, $headerH)),
    [System.Drawing.Color]::FromArgb(28, 90, 180),
    [System.Drawing.Color]::FromArgb(19, 155, 170),
    [System.Drawing.Drawing2D.LinearGradientMode]::Horizontal
)
$graphics.FillRectangle($headerBrush, 0, 0, $width, $headerH)
$graphics.DrawString($metricTitle, $titleFont, $white, $titleX, 48)
$graphics.DrawString($metricSubtitle, $subtitleFont, $white, $subtitleX, 124)
$graphics.DrawString("名次", $headerFont, $white, $headerRankX, 198)
$graphics.DrawString("精灵图", $headerFont, $white, $headerImageX, 198)
$graphics.DrawString("精灵名称", $headerFont, $white, $headerNameX, 198)
$graphics.DrawString($metricLabel, $headerFont, $white, $headerMetricX, 198)

$maxMetric = To-Int $ranked[0].$Metric
$minMetric = To-Int $ranked[-1].$Metric
$imgBox = 112

$i = 0
foreach ($row in $ranked) {
    $i++
    $y = $headerH + ($i - 1) * $rowH
    $rowBrush = if ($i % 2 -eq 1) {
        New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 255))
    } else {
        New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(241, 247, 253))
    }
    $graphics.FillRectangle($rowBrush, 0, $y, $width, $rowH)
    $rowBrush.Dispose()
    $graphics.DrawLine($linePen, $lineL, $y + $rowH - 1, $lineR, $y + $rowH - 1)

    $rankColor = if ($i -eq 1) {
        [System.Drawing.Color]::FromArgb(245, 158, 11)
    } elseif ($i -eq 2) {
        [System.Drawing.Color]::FromArgb(100, 116, 139)
    } elseif ($i -eq 3) {
        [System.Drawing.Color]::FromArgb(180, 83, 9)
    } else {
        [System.Drawing.Color]::FromArgb(30, 100, 210)
    }
    $rankBrush = New-Object System.Drawing.SolidBrush($rankColor)
    $graphics.FillEllipse($rankBrush, $rankX, $y + 47, 56, 56)
    $rankRect = New-Object System.Drawing.RectangleF -ArgumentList $rankX, ($y + 47), 56, 56
    if ($i -ge 100) {
        $rankFontForRow = New-Font 21 ([System.Drawing.FontStyle]::Bold)
        Draw-CenteredText $graphics ([string]$i) $rankFontForRow $white $rankRect
        $rankFontForRow.Dispose()
    } else {
        Draw-CenteredText $graphics ([string]$i) $rankFont $white $rankRect
    }
    $rankBrush.Dispose()

    $name = if ($row.display_name) { [string]$row.display_name } else { [string]$row.name }
    $number = [string]$row.number
    $metricValue = To-Int $row.$Metric
    $imageUrl = [string]$row.image_url
    $safeName = Safe-FileName ("{0:D2}_{1}_{2}.png" -f $i, $number, $name)
    $localImage = Join-Path $ImageCacheDir $safeName

    try {
        if (-not (Test-Path -LiteralPath $localImage)) {
            $cachedImage = Find-CachedImage $number $name
            if ($cachedImage) {
                Copy-Item -LiteralPath $cachedImage -Destination $localImage -Force
            } else {
                Download-Image $imageUrl $localImage
            }
        }
    } catch {
        Write-Warning "Failed to download image for $name : $($_.Exception.Message)"
    }

    $imgBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(232, 241, 250))
    Fill-RoundedRectangle $graphics $imgBg $imageX ($y + 18) $imgBox $imgBox 18
    $imgBg.Dispose()

    if (Test-Path -LiteralPath $localImage) {
        try {
            $img = [System.Drawing.Image]::FromFile($localImage)
            $scale = [Math]::Min(($imgBox - 12) / $img.Width, ($imgBox - 12) / $img.Height)
            $drawW = [int]($img.Width * $scale)
            $drawH = [int]($img.Height * $scale)
            $drawX = $imageX + [int](($imgBox - $drawW) / 2)
            $drawY = $y + 18 + [int](($imgBox - $drawH) / 2)
            $graphics.DrawImage($img, $drawX, $drawY, $drawW, $drawH)
            $img.Dispose()
        } catch {
            $graphics.DrawString("无图", $smallFont, $muted, ($imageX + 37), $y + 63)
        }
    } else {
        $graphics.DrawString("无图", $smallFont, $muted, ($imageX + 37), $y + 63)
    }

    $nameFont = Fit-Font $graphics $name 34 22 $nameMaxW ([System.Drawing.FontStyle]::Bold)
    $graphics.DrawString($name, $nameFont, $dark, $nameX, $y + 40)
    $graphics.DrawString(("编号 {0}  |  总和 {1}  |  速度 {2}" -f $number, (To-Int $row.stats_total), (To-Int $row.speed)), $smallFont, $muted, ($nameX + 2), $y + 88)
    $nameFont.Dispose()

    $barBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 232, 246))
    Fill-RoundedRectangle $graphics $barBg $barX ($y + 62) $barW 22 11
    $barBg.Dispose()
    $ratio = if ($maxMetric -eq $minMetric) { 1 } else { ($metricValue - $minMetric + 8) / ($maxMetric - $minMetric + 8) }
    $fillW = [Math]::Max(24, [int]($barW * $ratio))
    $barFill = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(30, 100, 210))
    Fill-RoundedRectangle $graphics $barFill $barX ($y + 62) $fillW 22 11
    $barFill.Dispose()

    $metricText = [string]$metricValue
    $metricSize = $graphics.MeasureString($metricText, $metricFont)
    $graphics.DrawString($metricText, $metricFont, $blue, $metricRight - $metricSize.Width, $y + 45)
}

$footerY = $height - $footerH
$footerBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(232, 241, 250))
$graphics.FillRectangle($footerBrush, 0, $footerY, $width, $footerH)
$footerBrush.Dispose()
$dateText = Get-Date -Format "yyyy-MM-dd"
$graphics.DrawString(("数据来源：本地 roco_world_data 精灵库 / BWiki 洛克王国：世界；生成日期：{0}" -f $dateText), $smallFont, $muted, $footerX, $footerY + 26)

$outputPath = Join-Path $OutputDir $OutputName
$bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$graphics.Dispose()
$bitmap.Dispose()
$headerBrush.Dispose()
$titleFont.Dispose()
$subtitleFont.Dispose()
$headerFont.Dispose()
$rankFont.Dispose()
$metricFont.Dispose()
$smallFont.Dispose()
$dark.Dispose()
$muted.Dispose()
$blue.Dispose()
$linePen.Dispose()

Write-Output $outputPath
Write-Output $csvPath


