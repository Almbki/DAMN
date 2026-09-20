# 方向5 补充检索：认知负荷经典文献 — OpenAlex API
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
  @{ k = "cl2_theory_classic";      q = "cognitive load theory instructional design" },
  @{ k = "cl2_element_interactivity";q = "element interactivity intrinsic extraneous germane cognitive load" },
  @{ k = "cl2_expertise_reversal";  q = "expertise reversal effect" },
  @{ k = "cl2_mental_fatigue_meta"; q = "mental fatigue meta-analysis performance" },
  @{ k = "cl2_rest_breaks";         q = "rest breaks work performance fatigue" },
  @{ k = "cl2_spacing";             q = "distributed practice spacing effect meta-analysis" },
  @{ k = "cl2_interleaving";        q = "interleaved practice mathematics learning" },
  @{ k = "cl2_nasa_tlx";            q = "NASA-TLX workload development" },
  @{ k = "cl2_multiple_resources";  q = "multiple resources mental workload prediction" },
  @{ k = "cl2_cognitive_effort";    q = "cognitive effort avoidance demand" },
  @{ k = "cl2_time_on_task";        q = "time on task performance decrement vigilance" },
  @{ k = "cl2_workload_performance";q = "mental workload performance decrement" },
  @{ k = "cl2_cognitive_offload";   q = "cognitive offloading working memory" }
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

