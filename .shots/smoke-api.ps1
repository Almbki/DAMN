# Backend contract smoke test:
# register -> login -> /users/me -> generate plan -> read plan -> patch task -> insights
# Usage: & .shots\smoke-api.ps1 [-Base http://192.168.9.67:8000]
# NOTE: ASCII only. Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI and mangles non-ASCII.
param(
  [string]$Base = "http://192.168.9.67:8000",
  [string]$Email = "agent-smoke@example.com",
  [string]$Password = "password123"
)

$ErrorActionPreference = "Stop"
$api = "$Base/api/v1"

function Show($label, $value) {
  Write-Output "--- $label ---"
  if ($null -eq $value) { Write-Output "<null>"; return }
  $json = $value | ConvertTo-Json -Depth 6 -Compress
  if ($json.Length -gt 1200) { $json = $json.Substring(0, 1200) + " ...[truncated]" }
  Write-Output $json
}

Show "health" (Invoke-RestMethod -Uri "$Base/health" -TimeoutSec 10)

try {
  $reg = Invoke-RestMethod -Uri "$api/auth/register" -Method Post -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password; display_name = "Smoke" } | ConvertTo-Json) -TimeoutSec 15
  Show "register" $reg
} catch {
  Write-Output "--- register --- skipped: $($_.Exception.Message)"
}

$tok = (Invoke-RestMethod -Uri "$api/auth/login" -Method Post -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) -TimeoutSec 15).access_token
Write-Output "--- login --- token length $($tok.Length)"

$h = @{ Authorization = "Bearer $tok" }
Show "users/me" (Invoke-RestMethod -Uri "$api/users/me" -Headers $h -TimeoutSec 15)

$body = @{
  goals = @(@{
      title             = "gaoshu limits review"
      description       = "watch`ndo examples`npractice"
      subject           = "math"
      estimated_minutes = 120
      priority          = 3
    })
  plan_title = "Smoke Plan"
} | ConvertTo-Json -Depth 6

$sw = [Diagnostics.Stopwatch]::StartNew()
$gen = Invoke-RestMethod -Uri "$api/plans/generate" -Method Post -Headers $h -ContentType "application/json" -Body $body -TimeoutSec 180
$sw.Stop()
Write-Output "--- generate --- took $($sw.ElapsedMilliseconds) ms"
Write-Output "job_id=$($gen.job_id) status=$($gen.status) plan_id=$($gen.plan_id) events_url=$($gen.events_url)"
Write-Output "plan inline? $($null -ne $gen.plan)"

$plans = Invoke-RestMethod -Uri "$api/plans" -Headers $h -TimeoutSec 20
Show "plans (list)" $plans

$planId = if ($gen.plan_id) { $gen.plan_id } else { $plans[0].id }
$plan = Invoke-RestMethod -Uri "$api/plans/$planId" -Headers $h -TimeoutSec 20
Write-Output "--- plan $planId --- tasks=$($plan.tasks.Count) goals=$($plan.goals.Count) status=$($plan.status) v$($plan.version)"
$plan.tasks | Select-Object -First 3 | ForEach-Object {
  Write-Output "  task#$($_.id) [$($_.status)] $($_.title) est=$($_.estimated_duration) pred=$($_.predicted_duration) date=$($_.scheduled_date) $($_.start_time)-$($_.end_time) load=$($_.cognitive_load) standards=$(($_.standards | Measure-Object).Count)"
}
Write-Output "  raw task[0]:"
Write-Output ($plan.tasks[0] | ConvertTo-Json -Depth 5 -Compress)

$first = $plan.tasks | Where-Object { $_.status -ne "completed" } | Select-Object -First 1
if ($first) {
  $patched = Invoke-RestMethod -Uri "$api/plans/$planId/tasks/$($first.id)" -Method Patch -Headers $h -ContentType "application/json" `
    -Body (@{ completed = $true; actual_duration = 90; difficulty_feedback = 4; stress_after = 6 } | ConvertTo-Json) -TimeoutSec 20
  Write-Output "--- patch task#$($first.id) --- status=$($patched.status) (requested completed=true)"
}

Show "insights" (Invoke-RestMethod -Uri "$api/plans/$planId/insights" -Headers $h -TimeoutSec 20)
Show "replan/eligibility" (Invoke-RestMethod -Uri "$api/plans/$planId/replan/eligibility" -Headers $h -TimeoutSec 20)

Write-Output ""
Write-Output "PLAN_ID=$planId"
