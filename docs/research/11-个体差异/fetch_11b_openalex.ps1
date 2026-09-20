# 方向11 补充检索：个体差异经典文献 — OpenAlex API
$dir = Join-Path $PSScriptRoot "api"
$headers = @{ 'User-Agent' = 'lit-survey/1.0 (academic literature survey, mailto:research@example.com)' }

function Get-OpenAlex($url) {
  for ($attempt = 1; $attempt -le 6; $attempt++) {
    try {
      $resp = Invoke-WebRequest -Uri $url -Headers $headers -TimeoutSec 45 -SkipCertificateCheck
      return ($resp.Content | ConvertFrom-Json -AsHashtable)
    } catch {
      $wait = 10 + $attempt * 10
      Write-Output ("  retry #{0} after {1}s" -f $attempt, $wait)
      Start-Sleep -Seconds $wait
    }
  }
  throw "giving up after retries"
}

$queries = @(
  @{ k = "id2_skill_acquisition";  q = "individual differences skill acquisition meta-analysis" },
  @{ k = "id2_knowledge_tracing";  q = "knowledge tracing modeling student knowledge" },
  @{ k = "id2_self_efficacy";      q = "self-efficacy academic performance meta-analysis" },
  @{ k = "id2_tutoring_meta";      q = "intelligent tutoring systems meta-analysis learning" },
  @{ k = "id2_wm_capacity";        q = "working memory capacity individual differences" },
  @{ k = "id2_learner_model";      q = "learner model student model adaptation" },
  @{ k = "id2_prior_knowledge";    q = "prior knowledge learning interaction expertise reversal" },
  @{ k = "id2_self_regulated";     q = "self-regulated learning meta-analysis training" },
  @{ k = "id2_academic_predictors";q = "predictors academic performance meta-analysis psychological" },
  @{ k = "id2_cognitive_diagnosis";q = "cognitive diagnosis model adaptive testing" },
  @{ k = "id2_personalized_path";  q = "personalized learning path recommendation" },
  @{ k = "id2_learning_rate";      q = "learning rate estimation students" },
  @{ k = "id2_ability_skill";      q = "cognitive abilities skill acquisition Ackerman" }
)

foreach ($item in $queries) {
  $url = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($item.q))&per-page=20&select=id,title,doi,publication_year,authorships,primary_location,biblio,cited_by_count,type,language&mailto=research@example.com"
  try {
    $r = Get-OpenAlex $url
    $sb = New-Object System.Text.StringBuilder
    $i = 0
    foreach ($p in $r['results']) {
      $i++
      if (-not $p['title']) { continue }
      $journal = if ($p['primary_location'] -and $p['primary_location']['source']) { $p['primary_location']['source']['display_name'] } else { "" }
      $auth = ($p['authorships'] | ForEach-Object { $_.author.display_name }) -join "; "
      $vol = $p['biblio']['volume']; $iss = $p['biblio']['issue']; $fp = $p['biblio']['first_page']; $lp = $p['biblio']['last_page']
      [void]$sb.AppendLine("### [$i] $($p['title'])")
      [void]$sb.AppendLine("YEAR=$($p['publication_year'])|CITED=$($p['cited_by_count'])|LANG=$($p['language'])|TYPE=$($p['type'])|DOI=$($p['doi'])|ID=$($p['id'])")
      [void]$sb.AppendLine("JOURNAL: $journal | VOL=$vol ISSUE=$iss PAGES=$fp-$lp")
      [void]$sb.AppendLine("AUTHORS: $auth")
      [void]$sb.AppendLine("")
    }
    Set-Content -LiteralPath (Join-Path $dir ($item.k + ".txt")) -Value $sb.ToString() -Encoding utf8
    Write-Output ("OK {0}: {1} items" -f $item.k, $i)
    Start-Sleep -Seconds 2
  } catch {
    Write-Output ("FAIL {0}: {1}" -f $item.k, $_.Exception.Message)
  }
}

