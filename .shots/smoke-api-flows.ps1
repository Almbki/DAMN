# Second-pass smoke: the exact request bodies the app sends.
# Covers: single-line goal, status=in_progress/skipped, uncheck (completed=false),
#         feedback with a REAL completion_rate -> auto-replan -> cooldown 409.
# Usage: & .shots\smoke-api-flows.ps1
# NOTE: ASCII only (Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI).
param(
  [string]$Base = "http://192.168.9.67:8000",
  [string]$Email = "agent-smoke@example.com",
  [string]$Password = "password123"
)

$ErrorActionPreference = "Stop"
$api = "$Base/api/v1"

$tok = (Invoke-RestMethod -Uri "$api/auth/login" -Method Post -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) -TimeoutSec 15).access_token
$h = @{ Authorization = "Bearer $tok" }
Write-Output "logged in"

# 1) Single-line goal, no description -> how many standards?
$body = @{ goals = @(@{ title = "single line goal" }); plan_title = "single line goal" } | ConvertTo-Json -Depth 6
$gen = Invoke-RestMethod -Uri "$api/plans/generate" -Method Post -Headers $h -ContentType "application/json" -Body $body -TimeoutSec 180
$planId = $gen.plan_id
$plan = Invoke-RestMethod -Uri "$api/plans/$planId" -Headers $h -TimeoutSec 20
Write-Output "1) single-line goal -> plan $planId, tasks=$($plan.tasks.Count)"
$plan.tasks | ForEach-Object { Write-Output "   task#$($_.id) standards=$(($_.standards | Measure-Object).Count) est=$($_.estimated_duration) status=$($_.status)" }

$taskId = $plan.tasks[0].id
function Patch($bodyObj) {
  Invoke-RestMethod -Uri "$api/plans/$planId/tasks/$taskId" -Method Patch -Headers $h -ContentType "application/json" `
    -Body ($bodyObj | ConvertTo-Json) -TimeoutSec 20
}

# 2) status transitions the UI actually sends
Write-Output "2) PATCH status=in_progress -> $((Patch @{ status = 'in_progress' }).status)"
Write-Output "   PATCH status=skipped     -> $((Patch @{ status = 'skipped' }).status)"
Write-Output "   PATCH completed=true     -> $((Patch @{ completed = $true }).status)"
Write-Output "   PATCH completed=false    -> $((Patch @{ completed = $false }).status)"

# 3) feedback with completion_rate below 0.5 -> auto replan?
$today = (Get-Date).ToString("yyyy-MM-dd")
$fb = @{ date = $today; completion_rate = 0.0; energy_level = 7; stress_level = 4; free_text = "mood: ok" } | ConvertTo-Json
$res = Invoke-RestMethod -Uri "$api/plans/$planId/feedback" -Method Post -Headers $h -ContentType "application/json" -Body $fb -TimeoutSec 180
Write-Output "3) feedback -> replan_triggered=$($res.replan_triggered) replan_plan_id=$($res.replan_plan_id)"
Write-Output "   eligibility: $($res.replan_eligibility | ConvertTo-Json -Compress)"

# 4) cooldown: a second manual replan must 409 with replan_not_eligible
try {
  $r = Invoke-RestMethod -Uri "$api/plans/$planId/replan" -Method Post -Headers $h -ContentType "application/json" `
    -Body (@{ trigger_type = 'manual'; reason = 'push rest to tomorrow' } | ConvertTo-Json) -TimeoutSec 180
  Write-Output "4) replan -> v$($r.new_version) (no cooldown hit)"
} catch {
  $resp = $_.Exception.Response
  $code = [int]$resp.StatusCode
  $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
  $payload = $reader.ReadToEnd()
  Write-Output "4) replan -> HTTP $code body=$payload"
}

# 5) insights for the NEWEST plan (a replan may have created one)
$list = Invoke-RestMethod -Uri "$api/plans" -Headers $h -TimeoutSec 20
Write-Output "5) plans: $(($list | ForEach-Object { "#$($_.id) v$($_.version) $($_.status) tasks=$($_.task_count) done=$($_.completed_count)" }) -join ' | ')"
$newest = $list[0]
$ins = Invoke-RestMethod -Uri "$api/plans/$($newest.id)/insights" -Headers $h -TimeoutSec 20
Write-Output "   insights(#$($newest.id)): total=$($ins.total_tasks) done=$($ins.completed_tasks) rate=$($ins.completion_rate) planned=$($ins.total_planned_minutes) actual=$($ins.total_actual_minutes) ratio=$($ins.predicted_vs_actual_ratio)"
Write-Output "   recommendations: $($ins.recommendations -join ' | ')"
