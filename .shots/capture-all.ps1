# Capture the whole app in one go: 9 viewports/schemes, light + dark, with and without
# a real session, and print a compact per-run summary.
#
# Edge headless needs named pipes for IPC, which the confined sandbox denies
# (FATAL:mojo platform_channel ... 0x5). Run this whole script once with relaxed file
# access instead of escalating per capture.
#
# ASCII only: PS 5.1 reads BOM-less .ps1 as ANSI.
param(
  [string]$Base = "http://192.168.9.67:8000",
  [string]$App = "http://localhost:8081",
  [string]$Email = "agent-smoke@example.com",
  [string]$Password = "password123"
)

$api = "$Base/api/v1"
$tok = (Invoke-RestMethod -Uri "$api/auth/login" -Method Post -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) -TimeoutSec 15).access_token
Write-Output "session token acquired (len=$($tok.Length))"

$reports = Join-Path $PSScriptRoot "reports"
New-Item -ItemType Directory -Force -Path $reports | Out-Null

$shots = @(
  @{ name = "login-390-light";      url = "$App/";           w = 390;  h = 844; scheme = 1; auth = $false },
  @{ name = "login-1440-dark";      url = "$App/";           w = 1440; h = 1000; scheme = 0; auth = $false },
  @{ name = "now-390-light";        url = "$App/";           w = 390;  h = 844; scheme = 1; auth = $true },
  @{ name = "now-1440-light";       url = "$App/";           w = 1440; h = 1000; scheme = 1; auth = $true },
  @{ name = "tasks-390-light";      url = "$App/tasks";      w = 390;  h = 844; scheme = 1; auth = $true },
  @{ name = "tasks-1440-dark";      url = "$App/tasks";      w = 1440; h = 1000; scheme = 0; auth = $true },
  @{ name = "assessment-390-light"; url = "$App/assessment"; w = 390;  h = 844; scheme = 1; auth = $true },
  @{ name = "review-1440-light";    url = "$App/review";     w = 1440; h = 1000; scheme = 1; auth = $true },
  @{ name = "account-390-light";    url = "$App/account";    w = 390;  h = 844; scheme = 1; auth = $true }
)

$index = 0
foreach ($shot in $shots) {
  $index++
  $env:CDP_OFFSET = $index
  $png = "$($shot.name).png"
  $nodeArgs = @(".shots/app-shot.js", $shot.url, $shot.w, $shot.h, $png, $shot.scheme)
  if ($shot.auth) { $nodeArgs += $tok }

  $raw = & node @nodeArgs 2>&1 | Out-String
  $jsonPath = Join-Path $reports "$($shot.name).json"
  $raw | Out-File -FilePath $jsonPath -Encoding utf8

  Write-Output ""
  Write-Output ("=== {0}  ({1}x{2} {3}) ===" -f $shot.name, $shot.w, $shot.h, $(if ($shot.scheme -eq 1) { "light" } else { "dark" }))
  try {
    $json = $raw | ConvertFrom-Json
    Write-Output ("  viewport={0} scheme={1} scrollW={2} overflow={3} nav={4} inputs={5} buttons={6}" -f `
        $json.viewport, $json.scheme, $json.htmlScrollW, $json.overflowCount,
      ($json.navLinks | Measure-Object).Count, ($json.inputs | Measure-Object).Count, ($json.buttons | Measure-Object).Count)
    if ($json.overflowCount -gt 0) {
      $json.overflowing | Select-Object -First 4 | ForEach-Object { Write-Output ("    OVERFLOW <{0}> right={1} w={2} '{3}'" -f $_.tag, $_.right, $_.w, $_.text) }
    }
    if ($json.navLinks) {
      Write-Output ("    nav: " + (($json.navLinks | ForEach-Object { "$($_.text)/$($_.w)x$($_.h)" }) -join "  "))
    }
    if ($json.consoleLogs) {
      $json.consoleLogs | Select-Object -First 4 | ForEach-Object { Write-Output ("    console: " + $_.Substring(0, [Math]::Min(150, $_.Length))) }
    } else {
      Write-Output "    console: (clean)"
    }
    Write-Output ("    text: " + ($json.text -replace "`r?`n", " | ").Substring(0, [Math]::Min(320, $json.text.Length)))
  } catch {
    Write-Output ("  JSON parse failed, raw head:")
    Write-Output ($raw.Substring(0, [Math]::Min(400, $raw.Length)))
  }
}

Write-Output ""
Write-Output "reports in $reports"
