# Seed the smoke account with a realistic multi-task plan so the UI screenshots show
# real data (the auto-replan earlier left it with a 0-task plan).
# ASCII only: PS 5.1 reads BOM-less .ps1 as ANSI.
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

$body = @{
  plan_title = "biye lunwen chongci"
  goals      = @(
    @{
      title             = "write chapter 3 of the thesis"
      description       = "draft the opening 300 words`nlist the 3 claims`nfind 2 references"
      goal_type         = "project"
      priority          = 3
      estimated_minutes = 120
      subject           = "thesis"
    },
    @{
      title             = "rehearse the defense slides"
      description       = "outline 10 slides`nspeak it once out loud"
      goal_type         = "short_term"
      priority          = 2
      estimated_minutes = 90
    },
    @{
      title             = "review calculus limits"
      goal_type         = "habit"
      priority          = 1
      estimated_minutes = 60
      subject           = "math"
    }
  )
} | ConvertTo-Json -Depth 6

$gen = Invoke-RestMethod -Uri "$api/plans/generate" -Method Post -Headers $h -ContentType "application/json" -Body $body -TimeoutSec 180
$plan = Invoke-RestMethod -Uri "$api/plans/$($gen.plan_id)" -Headers $h -TimeoutSec 20
$today = (Get-Date).ToString("yyyy-MM-dd")

Write-Output "plan #$($gen.plan_id) v$($plan.version) $($plan.start_date) .. $($plan.end_date) tasks=$($plan.tasks.Count)"
$plan.tasks | Sort-Object scheduled_date, start_time | ForEach-Object {
  $mark = if ($_.scheduled_date -eq $today) { "TODAY" } else { "     " }
  Write-Output ("  {0} task#{1} {2} {3} {4} pred={5} load={6} standards={7}" -f $mark, $_.id, $_.scheduled_date, $_.start_time, $_.title, $_.predicted_duration, $_.cognitive_load, ($_.standards | Measure-Object).Count)
}
Write-Output "today=$today  todayTasks=$(($plan.tasks | Where-Object { $_.scheduled_date -eq $today } | Measure-Object).Count)"
Write-Output "PLAN_ID=$($gen.plan_id)"
