# 抓取候选文献元数据+摘要（OpenAlex 单篇接口）— 方向5 和 方向11
$headers = @{ 'User-Agent' = 'lit-survey/1.0 (academic literature survey, mailto:research@example.com)' }

function Get-Abstract($inv) {
  if (-not $inv) { return "" }
  $words = @{}
  foreach ($k in $inv.Keys) { foreach ($pos in $inv[$k]) { $words[[int]$pos] = $k } }
  $out = for ($i = 0; $i -lt $words.Count; $i++) { $words[$i] }
  $s = ($out -join " ")
  if ($s.Length -gt 2500) { $s = $s.Substring(0, 2500) }
  return $s
}

function Get-DoiRecord($doi) {
  $u = "https://api.openalex.org/works/doi:$doi`?select=id,title,doi,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_location,biblio,type&mailto=research@example.com"
  for ($attempt = 1; $attempt -le 7; $attempt++) {
    try {
      $resp = Invoke-WebRequest -Uri $u -Headers $headers -TimeoutSec 45 -SkipCertificateCheck
      return ($resp.Content | ConvertFrom-Json -AsHashtable)
    } catch {
      if ($_.Exception.Response.StatusCode.value__ -eq 404) { return $null }
      $wait = 8 + $attempt * 8
      Write-Output ("  retry #{0} ({1}) after {2}s" -f $attempt, $doi, $wait)
      Start-Sleep -Seconds $wait
    }
  }
  return $null
}

function Process-List($pairs, $outFile) {
  $sb = New-Object System.Text.StringBuilder
  $n = 0
  foreach ($pair in $pairs) {
    $n++
    $r = Get-DoiRecord $pair.doi
    if (-not $r) { Write-Output ("MISS {0} {1}" -f $n, $pair.doi); continue }
    $journal = if ($r['primary_location'] -and $r['primary_location']['source']) { $r['primary_location']['source']['display_name'] } else { "" }
    $auth = ($r['authorships'] | ForEach-Object { $_.author.display_name }) -join "; "
    $vol = ""; $iss = ""; $fp = ""; $lp = ""
    if ($r['biblio']) { $vol = $r['biblio']['volume']; $iss = $r['biblio']['issue']; $fp = $r['biblio']['first_page']; $lp = $r['biblio']['last_page'] }
    [void]$sb.AppendLine("### [$n] $($r['title'])")
    [void]$sb.AppendLine("YEAR=$($r['publication_year'])|CITED=$($r['cited_by_count'])|TYPE=$($r['type'])|DOI=$($r['doi'])|ID=$($r['id'])")
    [void]$sb.AppendLine("JOURNAL: $journal | VOL=$vol ISSUE=$iss PAGES=$fp-$lp")
    [void]$sb.AppendLine("AUTHORS: $auth")
    [void]$sb.AppendLine("ABSTRACT: $(Get-Abstract $r['abstract_inverted_index'])")
    [void]$sb.AppendLine("")
    Write-Output ("OK {0}: {1}" -f $n, $r['title'])
    Start-Sleep -Milliseconds 1500
  }
  Set-Content -LiteralPath $outFile -Value $sb.ToString() -Encoding utf8
}

$pairs05 = @(
  @{ doi = "10.1007/s10648-010-9128-5" },
  @{ doi = "10.1007/s10648-019-09465-5" },
  @{ doi = "10.1007/s10648-007-9054-3" },
  @{ doi = "10.1016/j.learninstruc.2025.102142" },
  @{ doi = "10.1518/001872008x288394" },
  @{ doi = "10.1146/annurev-neuro-072116-031526" },
  @{ doi = "10.1016/s0166-4115(08)62386-9" },
  @{ doi = "10.1080/00140139.2014.956151" },
  @{ doi = "10.1037/a0020198" },
  @{ doi = "10.3758/s13415-015-0334-y" },
  @{ doi = "10.1518/001872008x312152" },
  @{ doi = "10.1007/s40279-016-0672-0" },
  @{ doi = "10.1518/001872007x312496" },
  @{ doi = "10.1016/s0169-8141(96)00029-7" },
  @{ doi = "10.1007/s00221-011-2749-1" },
  @{ doi = "10.1080/0267837031000155949" },
  @{ doi = "10.1016/j.cognition.2010.12.007" },
  @{ doi = "10.1002/job.541" },
  @{ doi = "10.3389/fpsyg.2022.867978" },
  @{ doi = "10.1037/0033-2909.132.3.354" },
  @{ doi = "10.1037/edu0000001" },
  @{ doi = "10.1037/edu0000367" },
  @{ doi = "10.1177/1529100612453266" },
  @{ doi = "10.1371/journal.pdig.0001281" },
  @{ doi = "10.3390/bioengineering13070734" }
)

$pairs11 = @(
  @{ doi = "10.1037//1076-898x.6.4.259" },
  @{ doi = "10.1037/1076-898x.1.4.270" },
  @{ doi = "10.1016/s1389-0417(01)00049-3" },
  @{ doi = "10.1016/j.actpsy.2026.106279" },
  @{ doi = "10.3389/fpsyg.2019.03087" },
  @{ doi = "10.1037/0033-295x.99.1.122" },
  @{ doi = "10.1111/1467-8721.00160" },
  @{ doi = "10.3758/bf03196323" },
  @{ doi = "10.1007/bf01099821" },
  @{ doi = "10.48550/arxiv.1506.05908" },
  @{ doi = "10.1007/978-3-642-39112-5_18" },
  @{ doi = "10.1145/3569576" },
  @{ doi = "10.1007/s11257-011-9106-8" },
  @{ doi = "10.1037/a0026838" },
  @{ doi = "10.1037/0033-2909.130.2.261" },
  @{ doi = "10.1016/j.lindif.2017.11.015" },
  @{ doi = "10.3389/fpsyg.2026.1769823" },
  @{ doi = "10.2147/AMEP.S591397" },
  @{ doi = "10.1037/a0022777" },
  @{ doi = "10.3389/fpsyg.2017.00422" },
  @{ doi = "10.1016/j.cedpsych.2021.101976" },
  @{ doi = "10.1037/a0037123" },
  @{ doi = "10.1037/a0034752" },
  @{ doi = "10.1186/s40561-019-0089-y" },
  @{ doi = "10.1111/bjet.13334" }
)

Write-Output "=== 方向5 ==="
Process-List $pairs05 ("doc/research/05-认知负荷/api/pick_05.txt")
Write-Output "=== 方向11 ==="
Process-List $pairs11 ("doc/research/11-个体差异/api/pick_11.txt")

