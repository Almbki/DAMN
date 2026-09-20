# Real click-through verification, objective version.
#
# The console text prints are UTF-8 from node but pass through PS 5.1, so non-ASCII can
# look mangled here -- the AUTHORITATIVE evidence is the server state printed after each
# click (re-read from the backend), not the on-screen text.
#
# Targets are ASCII or the structural "@primary" selector on purpose: PS 5.1 reads
# BOM-less UTF-8 scripts as ANSI, so passing Chinese button labels as arguments breaks.
#
# ASCII only for the same reason.
param(
  [string]$Base = "http://192.168.9.67:8000",
  [string]$App = "http://localhost:8081",
  [string]$Email = "agent-smoke@example.com",
  [string]$Password = "password123"
)

$tok = (Invoke-RestMethod -Uri "$Base/api/v1/auth/login" -Method Post -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) -TimeoutSec 15).access_token
$h = @{ Authorization = "Bearer $tok" }

function ShowState([string]$label) {
  $list = Invoke-RestMethod -Uri "$Base/api/v1/plans" -Headers $h -TimeoutSec 20
  $plan = Invoke-RestMethod -Uri "$Base/api/v1/plans/$($list[0].id)" -Headers $h -TimeoutSec 20
  Write-Output ("  [{0}] plan #{1} v{2}" -f $label, $plan.id, $plan.version)
  $plan.tasks | Sort-Object scheduled_date, start_time | ForEach-Object {
    Write-Output ("    task#{0} status={1} '{2}'" -f $_.id, $_.status, $_.title)
  }
}

Write-Output "=== state BEFORE ==="
ShowState "before"

$env:CDP_OFFSET = "1"
Write-Output "=== PROBE A: / -> click @primary (expect in_progress) ==="
& node .shots/app-click.js "$App/" "probe-a-start.png" $tok "@primary" 1 2>&1 | Select-String -Pattern "click #|not found|console:|^shot:" | Out-String
ShowState "after A"

$env:CDP_OFFSET = "2"
Write-Output "=== PROBE B: / -> click @primary again (expect completed + next task current) ==="
& node .shots/app-click.js "$App/" "probe-b-complete.png" $tok "@primary" 1 2>&1 | Select-String -Pattern "click #|not found|console:|^shot:" | Out-String
ShowState "after B"

$env:CDP_OFFSET = "3"
Write-Output "=== PROBE C: /tasks -> click the 'review calculus' checkbox ==="
& node .shots/app-click.js "$App/tasks" "probe-c-check.png" $tok "review calculus" 1 2>&1 | Select-String -Pattern "click #|not found|console:|^shot:" | Out-String
ShowState "after C"
