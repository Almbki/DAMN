# 方向9 检索：反馈调节/自适应规划 — OpenAlex API
$dir = Join-Path $PSScriptRoot "api"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$headers = @{ 'User-Agent' = 'lit-survey/1.0 (academic literature survey, mailto:research@example.com)' }

function Get-OpenAlex($url) {
  for ($attempt = 1; $attempt -le 6; $attempt++) {
    try {
      $resp = Invoke-WebRequest -Uri $url -Headers $headers -TimeoutSec 45 -SkipCertificateCheck
      return $resp.Content
    } catch {
      $wait = 8 + $attempt * 8
      Write-Output ("  retry #{0} after {1}s" -f $attempt, $wait)
      Start-Sleep -Seconds $wait
    }
  }
  throw "giving up after retries"
}

$queries = @(
  @{ k = "fb_adaptive_planning";        q = "adaptive planning feedback" },
  @{ k = "fb_closed_loop_planning";     q = "closed-loop planning feedback system" },
  @{ k = "fb_feedback_scheduling";      q = "feedback-driven scheduling" },
  @{ k = "fb_dynamic_replanning";       q = "dynamic replanning autonomous" },
  @{ k = "fb_plan_repair";              q = "plan repair replanning agent" },
  @{ k = "fb_adaptive_scheduling_human";q = "adaptive scheduling human performance" },
  @{ k = "fb_personalized_intervention";q = "personalized intervention adaptive" },
  @{ k = "fb_feedback_control_behavior";q = "feedback control human behavior change" },
  @{ k = "fb_human_in_the_loop";        q = "human-in-the-loop planning optimization" },
  @{ k = "fb_adaptive_goal_setting";    q = "adaptive goal setting performance" },
  @{ k = "fb_goal_adjustment";          q = "goal adjustment feedback motivation" },
  @{ k = "fb_goal_setting_theory";      q = "goal setting theory feedback performance" },
  @{ k = "fb_feedback_frequency";       q = "feedback frequency performance learning" },
  @{ k = "fb_control_theory";           q = "control theory self-regulation behavior" },
  @{ k = "fb_rl_intervention";          q = "reinforcement learning adaptive intervention" },
  @{ k = "fb_jitai";                    q = "just-in-time adaptive intervention" },
  @{ k = "fb_adaptive_trial";           q = "adaptive intervention sequential decision" },
  @{ k = "fb_dynamic_treatment";        q = "dynamic treatment regime personalized" },
  @{ k = "fb_mpc_human";                q = "model predictive control human behavior" },
  @{ k = "fb_task_difficulty_adapt";    q = "adaptive task difficulty selection training" },
  @{ k = "fb_state_estimation";         q = "state estimation user model adaptation" },
  @{ k = "fb_selfregulated_feedback";   q = "self-regulated learning feedback loop" },
  @{ k = "fb_adaptive_task_selection";  q = "adaptive task selection learner model" },
  @{ k = "fb_oscillation_stability";    q = "stability oscillation feedback control planning" },
  @{ k = "fb_replanning_scheduling";    q = "rescheduling feedback disruption" },
  @{ k = "fb_goal_persistence";         q = "goal persistence long-term short-term adjustment" },
  @{ k = "fb_engagement_adaptation";    q = "engagement detection adaptive tutoring" },
  @{ k = "fb_bandit_recommendation";    q = "multi-armed bandit adaptive recommendation education" }
)

foreach ($item in $queries) {
  $url = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($item.q))&per-page=25&select=id,title,doi,publication_year,authorships,primary_location,biblio,cited_by_count,type,language,abstract_inverted_index&mailto=research@example.com"
  try {
    $content = Get-OpenAlex $url
    Set-Content -LiteralPath (Join-Path $dir ("raw_" + $item.k + ".json")) -Value $content -Encoding utf8
    $r = $content | ConvertFrom-Json -AsHashtable
    Write-Output ("OK {0}: {1} items" -f $item.k, $r['results'].Count)
    Start-Sleep -Seconds 2
  } catch {
    Write-Output ("FAIL {0}: {1}" -f $item.k, $_.Exception.Message)
  }
}
