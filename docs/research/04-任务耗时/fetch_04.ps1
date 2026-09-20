# 方向4：任务耗时/人类表现预测 —— OpenAlex API 检索（curl 下载 raw JSON + System.Text.Json 解析）
$ErrorActionPreference = "Continue"
$dir = Join-Path $PSScriptRoot "api"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

function TryGet($el, $name) {
  if ($null -eq $el) { return $null }
  if ($el.ValueKind -ne [System.Text.Json.JsonValueKind]::Object -and $el.ValueKind -ne [System.Text.Json.JsonValueKind]::Array) { return $null }
  $v = [System.Text.Json.JsonElement]::new()
  if ($el.TryGetProperty($name, [ref]$v)) { return $v }
  return $null
}

function Get-Str($el) {
  if ($null -eq $el) { return "" }
  try { return $el.GetString() } catch { return "" }
}

function Write-RawToText($rawFile, $txtFile) {
  $doc = [System.Text.Json.JsonDocument]::Parse([System.IO.File]::ReadAllText($rawFile, [System.Text.Encoding]::UTF8))
  $sb = New-Object System.Text.StringBuilder
  $n = 0
  try {
    foreach ($el in $doc.RootElement.GetProperty('results').EnumerateArray()) {
      $title = Get-Str (TryGet $el 'title')
      if (-not $title) { continue }
      $n++
      $year = $cited = 0
      $y = TryGet $el 'publication_year'; if ($null -ne $y) { $year = $y.GetInt32() }
      $c = TryGet $el 'cited_by_count'; if ($null -ne $c) { $cited = $c.GetInt32() }
      $doi = (Get-Str (TryGet $el 'doi')).Replace('https://doi.org/', '')
      $id = Get-Str (TryGet $el 'id')
      $lang = Get-Str (TryGet $el 'language')
      $type = Get-Str (TryGet $el 'type')
      $journal = ""; $vol = ""; $iss = ""; $fp = ""; $lp = ""
      $pl = TryGet $el 'primary_location'
      if ($null -ne $pl) {
        $src = TryGet $pl 'source'
        if ($null -ne $src) { $journal = Get-Str (TryGet $src 'display_name') }
      }
      $b = TryGet $el 'biblio'
      if ($null -ne $b) {
        $vol = Get-Str (TryGet $b 'volume'); $iss = Get-Str (TryGet $b 'issue')
        $fp = Get-Str (TryGet $b 'first_page'); $lp = Get-Str (TryGet $b 'last_page')
      }
      $auths = @()
      $au = TryGet $el 'authorships'
      if ($null -ne $au -and $au.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
        foreach ($a in $au.EnumerateArray()) {
          $author = TryGet $a 'author'
          if ($null -ne $author) { $auths += (Get-Str (TryGet $author 'display_name')) }
        }
      }
      $abs = ""
      $inv = TryGet $el 'abstract_inverted_index'
      if ($null -ne $inv -and $inv.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
        $words = @{}
        foreach ($prop in $inv.EnumerateObject()) {
          foreach ($posEl in $prop.Value.EnumerateArray()) {
            $words[[int]$posEl.GetInt32()] = $prop.Name
          }
        }
        $w = for ($i = 0; $i -lt $words.Count; $i++) { $words[$i] }
        $abs = ($w -join " ")
        if ($abs.Length -gt 1800) { $abs = $abs.Substring(0, 1800) }
      }
      [void]$sb.AppendLine("### [$n] $title")
      [void]$sb.AppendLine("YEAR=$year|CITED=$cited|LANG=$lang|TYPE=$type|DOI=$doi|ID=$id")
      [void]$sb.AppendLine("JOURNAL: $journal | VOL=$vol ISSUE=$iss PAGES=$fp-$lp")
      [void]$sb.AppendLine("AUTHORS: $($auths -join '; ')")
      [void]$sb.AppendLine("ABSTRACT: $abs")
      [void]$sb.AppendLine("")
    }
  } finally {
    $doc.Dispose()
  }
  Set-Content -LiteralPath $txtFile -Value $sb.ToString() -Encoding utf8
  return $n
}

$queries = @(
  @{ k = "task_completion_time_prediction"; q = "task completion time prediction" },
  @{ k = "task_duration_prediction"; q = "task duration prediction" },
  @{ k = "time_on_task"; q = "time on task learning" },
  @{ k = "human_performance_prediction"; q = "human performance prediction" },
  @{ k = "individual_productivity"; q = "individual productivity prediction" },
  @{ k = "learning_time_prediction"; q = "learning time prediction" },
  @{ k = "individual_differences_performance"; q = "individual differences task performance" },
  @{ k = "planning_fallacy"; q = "planning fallacy" },
  @{ k = "software_effort_estimation"; q = "software effort estimation" },
  @{ k = "response_time_prediction"; q = "response time prediction cognitive" },
  @{ k = "effort_estimation_ml"; q = "effort estimation machine learning" },
  @{ k = "duration_prediction_ml"; q = "task duration prediction machine learning" },
  @{ k = "construction_productivity"; q = "construction labor productivity prediction" },
  @{ k = "learning_curve"; q = "learning curve practice power law" },
  @{ k = "human_performance_modeling"; q = "human performance modeling time" },
  @{ k = "cognitive_load_completion_time"; q = "cognitive load task completion time" },
  @{ k = "knowledge_work_productivity"; q = "knowledge worker productivity prediction" },
  @{ k = "time_estimation_calibration"; q = "time estimation calibration task" },
  @{ k = "scheduling_duration"; q = "duration prediction scheduling" },
  @{ k = "experience_curve"; q = "experience curve task time" },
  @{ k = "user_skill_time"; q = "skill and task completion time" },
  @{ k = "chinese_task_time"; q = "任务耗时预测" },
  @{ k = "chinese_completion_time"; q = "完成任务时间预测" },
  @{ k = "chinese_individual_difference"; q = "个体差异 任务表现" }
)

foreach ($item in $queries) {
  $url = "https://api.openalex.org/works?filter=title_and_abstract.search:$([uri]::EscapeDataString($item.q))&sort=relevance_score:desc&per-page=25&select=id,title,doi,publication_year,authorships,primary_location,biblio,cited_by_count,abstract_inverted_index,type,language&mailto=research@example.com"
  $rawFile = Join-Path $dir ("raw_" + $item.k + ".json")
  $txtFile = Join-Path $dir ($item.k + ".txt")
  $ok = $false
  if (Test-Path $rawFile) { $ok = $true }
  for ($try = 1; $try -le 4 -and -not $ok; $try++) {
    & curl.exe -sS --connect-timeout 25 --max-time 90 -A "lit-survey/4.0" -o $rawFile $url
    if ($LASTEXITCODE -eq 0 -and (Get-Item $rawFile).Length -gt 50) { $ok = $true; break }
    Start-Sleep -Seconds 8
  }
  if (-not $ok) { Write-Output ("FAIL DOWNLOAD {0}" -f $item.k); continue }
  try {
    $cnt = Write-RawToText $rawFile $txtFile
    Write-Output ("OK {0}: {1} items" -f $item.k, $cnt)
  } catch {
    Write-Output ("PARSE FAIL {0}: {1} @line {2}" -f $item.k, $_.Exception.Message, $_.InvocationInfo.ScriptLineNumber)
  }
  Start-Sleep -Seconds 2
}
