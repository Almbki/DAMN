# The marquee flow, clicked for real: type a goal on /goals -> generate -> land on /tasks.
# Evidence is the server: a NEW plan must exist afterwards, with the goal title and the
# second line turned into task standards.
#
# ASCII only (PS 5.1 reads BOM-less UTF-8 as ANSI). Empty $tok would silently shift every
# positional argument, so the token is validated before anything runs.
param(
  [string]$Base = "http://192.168.9.67:8000",
  [string]$App = "http://localhost:8081",
  [string]$Email = "agent-smoke@example.com",
  [string]$Password = "password123"
)

$tok = ""
for ($i = 1; $i -le 3 -and -not $tok; $i++) {
  try {
    $tok = (Invoke-RestMethod -Uri "$Base/api/v1/auth/login" -Method Post -ContentType "application/json" `
        -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) -TimeoutSec 90).access_token
  } catch {
    Write-Output "login attempt $i failed: $($_.Exception.Message)"
    Start-Sleep -Seconds 3
  }
}
if (-not $tok) { Write-Output "ABORT: no token (backend unreachable)"; exit 1 }
Write-Output "token ok (len=$($tok.Length))"

$h = @{ Authorization = "Bearer $tok" }
$before = Invoke-RestMethod -Uri "$Base/api/v1/plans" -Headers $h -TimeoutSec 90
Write-Output ("plans before: " + (($before | ForEach-Object { "#$($_.id)v$($_.version)" }) -join " "))

# Two lines on purpose: line 1 becomes the goal title, line 2 the description
# (which the backend turns into task standards).
$env:CLICK_TYPE_TEXT = "finish the half marathon plan`nbook a race`nwrite the weekly schedule"
$env:CDP_OFFSET = "9"
& node .shots/app-click.js "$App/goals" "probe-d-generate.png" $tok "@primary" 1 2>&1 |
  Select-String -Pattern "typed|click #|not found|console:|^shot:" | Out-String
$env:CLICK_TYPE_TEXT = $null

Write-Output "=== server state after generate ==="
$after = Invoke-RestMethod -Uri "$Base/api/v1/plans" -Headers $h -TimeoutSec 90
Write-Output ("plans after:  " + (($after | ForEach-Object { "#$($_.id)v$($_.version):$($_.status):tasks=$($_.task_count)" }) -join " "))
$newest = $after[0]
$plan = Invoke-RestMethod -Uri "$Base/api/v1/plans/$($newest.id)" -Headers $h -TimeoutSec 90
Write-Output "newest plan #$($plan.id) title='$($plan.title)' v$($plan.version)"
Write-Output "goals:"
$plan.goals | ForEach-Object { Write-Output ("  goal#{0} '{1}' type={2}" -f $_.id, $_.title, $_.goal_type) }
Write-Output "tasks:"
$plan.tasks | ForEach-Object { Write-Output ("  task#{0} '{1}' standards={2}" -f $_.id, $_.title, ($_.standards | Measure-Object).Count) }
