# 方向3：任务拆解 —— OpenAlex API 检索（curl 下载 raw JSON + System.Text.Json 解析）
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
  @{ k = "task_decomposition"; q = "task decomposition" },
  @{ k = "goal_decomposition"; q = "goal decomposition" },
  @{ k = "hierarchical_task_planning"; q = "hierarchical task planning" },
  @{ k = "hierarchical_task_network"; q = "hierarchical task network planning" },
  @{ k = "subgoal_learning"; q = "subgoal learning" },
  @{ k = "subgoal"; q = "subgoal" },
  @{ k = "task_granularity"; q = "task granularity" },
  @{ k = "task_chunking"; q = "task chunking" },
  @{ k = "goal_setting"; q = "goal setting theory" },
  @{ k = "implementation_intention"; q = "implementation intention" },
  @{ k = "proximal_goals"; q = "proximal goals" },
  @{ k = "goal_gradient"; q = "goal gradient hypothesis" },
  @{ k = "subgoal_labeling"; q = "subgoal labeling" },
  @{ k = "task_analysis"; q = "task analysis decomposition" },
  @{ k = "work_breakdown"; q = "work breakdown structure" },
  @{ k = "goal_hierarchy"; q = "hierarchical goal representation" },
  @{ k = "subgoal_feedback"; q = "subgoal feedback" },
  @{ k = "task_decomposition_llm"; q = "LLM task decomposition planning" },
  @{ k = "task_breakdown_procrastination"; q = "task breakdown procrastination" },
  @{ k = "goal_commitment"; q = "goal commitment motivation performance" },
  @{ k = "chinese_task_breakdown"; q = "任务拆解" },
  @{ k = "chinese_goal_setting"; q = "目标设置" },
  @{ k = "chinese_goal_breakdown"; q = "目标拆解" },
  @{ k = "chinese_subgoal"; q = "子目标" }
)

foreach ($item in $queries) {
  $url = "https://api.openalex.org/works?filter=title_and_abstract.search:$([uri]::EscapeDataString($item.q))&sort=relevance_score:desc&per-page=25&select=id,title,doi,publication_year,authorships,primary_location,biblio,cited_by_count,abstract_inverted_index,type,language&mailto=research@example.com"
  $rawFile = Join-Path $dir ("raw_" + $item.k + ".json")
  $txtFile = Join-Path $dir ($item.k + ".txt")
  $ok = $false
  if (Test-Path $rawFile) { $ok = $true }
  for ($try = 1; $try -le 4 -and -not $ok; $try++) {
    & curl.exe -sS --connect-timeout 25 --max-time 90 -A "lit-survey/3.0" -o $rawFile $url
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
