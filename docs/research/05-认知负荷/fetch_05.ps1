# 方向5：认知负荷 — 通过 PubMed E-utilities 实际检索
# 数据源: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ (NCBI)
$dir = Join-Path $PSScriptRoot "api"
$esearchBase = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=25&retmode=json&term="
$efetchBase  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id="

function Get-Retry($url, $attempts = 5) {
  for ($i = 1; $i -le $attempts; $i++) {
    try { return (Invoke-WebRequest -Uri $url -TimeoutSec 45 -SkipCertificateCheck) }
    catch { Start-Sleep -Seconds 4 }
  }
  throw "giving up: $url"
}

function Get-Abstract($article) {
  $abs = $article.MedlineCitation.Article.Abstract
  if (-not $abs) { return "" }
  $parts = @()
  foreach ($t in $abs.AbstractText) {
    if ($t -is [string]) { $parts += $t } else { $parts += $t.'#text' }
  }
  $s = ($parts -join ' ')
  if ($s.Length -gt 2000) { $s = $s.Substring(0, 2000) }
  return $s
}

function Get-Doi($article) {
  foreach ($el in $article.MedlineCitation.Article.ELocationID) {
    if ($el.EIdType -eq 'doi') { return $el.'#text' }
  }
  foreach ($aid in $article.PubmedData.ArticleIdList.ArticleId) {
    if ($aid.IdType -eq 'doi') { return $aid.'#text' }
  }
  return ""
}

function Get-Authors($article) {
  $al = $article.MedlineCitation.Article.AuthorList
  if (-not $al) { return "" }
  $names = @()
  foreach ($au in $al.Author) {
    $n = if ($au.CollectiveName) { $au.CollectiveName } else { "$($au.ForeName) $($au.LastName)" }
    $names += $n
  }
  return ($names -join "; ")
}

$queries = @(
  @{ k = "cl_task_complexity";  q = 'cognitive load[tiab] AND task complexity[tiab]' },
  @{ k = "cl_mental_workload";  q = 'mental workload[tiab] AND task performance[tiab]' },
  @{ k = "cl_theory";           q = 'cognitive load theory[tiab] AND (learning OR instruction)' },
  @{ k = "cl_intrinsic";        q = 'intrinsic cognitive load[tiab]' },
  @{ k = "cl_nasa_tlx";         q = 'NASA-TLX[tiab] AND workload[tiab]' },
  @{ k = "cl_difficulty_time";  q = 'task difficulty[tiab] AND completion time[tiab]' },
  @{ k = "cl_mental_fatigue";   q = 'mental fatigue[tiab] AND cognitive performance[tiab]' },
  @{ k = "cl_rest_break";       q = 'rest break[tiab] AND (fatigue[tiab] OR performance[tiab])' },
  @{ k = "cl_daily_workload";   q = 'workload[tiab] AND work schedule[tiab] AND performance[tiab]' },
  @{ k = "cl_task_switch";      q = 'task switching[tiab] AND cognitive cost[tiab]' },
  @{ k = "cl_scheduling";       q = 'task scheduling[tiab] AND cognitive[tiab]' },
  @{ k = "cl_overload";         q = 'cognitive overload[tiab] AND performance[tiab]' },
  @{ k = "cl_review_meta";      q = 'cognitive load[tiab] AND (review[pt] OR meta-analysis[pt])' }
)

foreach ($item in $queries) {
  try {
    $es = Get-Retry ($esearchBase + [uri]::EscapeDataString($item.q))
    $er = $es.Content | ConvertFrom-Json
    $ids = $er.esearchresult.idlist
    if (-not $ids -or $ids.Count -eq 0) { Write-Output ("EMPTY {0}" -f $item.k); continue }
    $ef = Get-Retry ($efetchBase + ($ids -join ','))
    $xml = [xml]$ef.Content
    $sb = New-Object System.Text.StringBuilder
    $i = 0
    foreach ($a in $xml.PubmedArticleSet.PubmedArticle) {
      $i++
      $title = $a.MedlineCitation.Article.ArticleTitle
      $jrnl = $a.MedlineCitation.Article.Journal.Title
      $year = $a.MedlineCitation.Article.Journal.JournalIssue.PubDate.Year
      if (-not $year) { $year = $a.MedlineCitation.Article.Journal.JournalIssue.PubDate.MedlineDate }
      $pmid = $a.MedlineCitation.PMID.InnerText
      $pt = ($a.MedlineCitation.Article.PublicationTypeList.PublicationType | ForEach-Object { $_.'#text' }) -join ","
      [void]$sb.AppendLine("### [$i] $title")
      [void]$sb.AppendLine("PMID=$pmid|YEAR=$year|PUBTYPE=$pt|DOI=$(Get-Doi $a)")
      [void]$sb.AppendLine("JOURNAL: $jrnl")
      [void]$sb.AppendLine("AUTHORS: $(Get-Authors $a)")
      [void]$sb.AppendLine("ABSTRACT: $(Get-Abstract $a)")
      [void]$sb.AppendLine("URL: https://pubmed.ncbi.nlm.nih.gov/$pmid/")
      [void]$sb.AppendLine("")
    }
    Set-Content -LiteralPath (Join-Path $dir ($item.k + ".txt")) -Value $sb.ToString() -Encoding utf8
    Write-Output ("OK {0}: {1} items" -f $item.k, $i)
    Start-Sleep -Milliseconds 700
  } catch {
    Write-Output ("FAIL {0}: {1}" -f $item.k, $_.Exception.Message)
  }
}

