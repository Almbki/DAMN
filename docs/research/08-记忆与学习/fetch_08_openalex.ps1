# 方向8 检索：学习、记忆与复习 — OpenAlex API
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
  @{ k = "mem_forgetting_curve";        q = "forgetting curve memory retention" },
  @{ k = "mem_spaced_repetition";       q = "spaced repetition learning effectiveness" },
  @{ k = "mem_spacing_effect";          q = "spacing effect learning retention" },
  @{ k = "mem_retrieval_practice";      q = "retrieval practice testing effect" },
  @{ k = "mem_distributed_practice";    q = "distributed practice learning" },
  @{ k = "mem_expanding_interval";      q = "expanding retrieval practice schedule" },
  @{ k = "mem_adaptive_spacing";        q = "adaptive spaced repetition scheduling algorithm" },
  @{ k = "mem_individual_forgetting";   q = "individual differences forgetting rate" },
  @{ k = "mem_retention_halflife";      q = "memory retention half-life decay model" },
  @{ k = "mem_personalized_review";     q = "personalized review scheduling learning" },
  @{ k = "mem_testing_meta";            q = "testing effect meta-analysis" },
  @{ k = "mem_spacing_meta";            q = "spacing effect meta-analysis" },
  @{ k = "mem_language_vocab";          q = "spaced repetition vocabulary learning" },
  @{ k = "mem_optimal_gap";             q = "optimal spacing gap retention" },
  @{ k = "mem_desirable_difficulty";    q = "desirable difficulties learning retention" },
  @{ k = "mem_flashcard_algorithm";     q = "flashcard scheduling algorithm memory" },
  @{ k = "mem_longterm_retention";      q = "long-term retention practice schedule" },
  @{ k = "mem_forgetting_prediction";   q = "forgetting prediction model student" },
  @{ k = "mem_retrieval_prior";         q = "prior knowledge retrieval practice" },
  @{ k = "mem_interleaving";            q = "interleaving practice learning" },
  @{ k = "mem_selfregulated_spacing";   q = "self-regulated spacing study" },
  @{ k = "mem_sleep_consolidation";     q = "sleep memory consolidation retention" },
  @{ k = "mem_retrieval_school";        q = "retrieval practice classroom achievement" },
  @{ k = "mem_memory_models";           q = "cognitive model memory decay activation" },
  @{ k = "mem_review_timing";           q = "review timing recall probability" },
  @{ k = "mem_metacognition_study";     q = "metacognition judgments of learning study time" }
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
