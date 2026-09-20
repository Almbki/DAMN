# 批量验证采纳文献 DOI（Crossref API）+ 无 DOI 的用 OpenAlex ID 验证
$dois = @{
  # ---- 方向2 ----
  "10.1037/0022-0167.31.4.503" = "Solomon & Rothblum 1984";
  "10.1080/00224545.1995.9712234" = "Seneccal 1995";
  "10.1016/j.cedpsych.2007.07.001" = "Klassen 2007";
  "10.1111/ap.12173" = "Steel & Klingsieck 2016";
  "10.1016/j.paid.2015.02.038" = "Kim & Seo 2015";
  "10.1016/s0191-8869(02)00358-6" = "van Eerde 2003";
  "10.12973/ijem.6.4.681" = "Akpur 2020";
  "10.3390/educsci14030323" = "Kooren 2024";
  "10.1016/j.edurev.2018.09.002" = "van Eerde & Klingsieck 2018";
  "10.3389/fpsyg.2018.00327" = "Steel 2018";
  "10.1111/1467-9280.00441" = "Ariely & Wertenbroch 2002";
  "10.1111/ecin.13042" = "Knowles 2021";
  "10.2466/pr0.96.3c.1015-1021" = "Tuckman 2005";
  "10.3389/fpsyg.2021.783789" = "Steel & Taras 2022";
  "10.1093/jeea/jvw015" = "Ericson 2017";
  "10.1016/j.paid.2019.109762" = "Svartdal 2019";
  "10.1177/0273475304273842" = "Ackerman & Gross 2005";
  "10.3200/socp.145.3.245-264" = "Chu & Choi 2005";
  "10.1111/spc3.12011" = "Sirois & Pychyl 2013";
  "10.1016/j.learninstruc.2013.09.005" = "Wachle 2013";
  "10.1016/j.lindif.2018.04.009" = "Ziegler 2018";
  "10.1002/j.1556-6676.1998.tb02548.x" = "Haycock 1998";
  # ---- 方向6 ----
  "10.5465/amj.2005.18803921" = "LePine 2005 meta";
  "10.1037/0021-9010.89.5.883" = "LePine 2004";
  "10.1002/job.2412" = "Mazzola 2019";
  "10.1037/edu0000478" = "Travis 2020";
  "10.5465/amj.2016.0646" = "Mitchell 2018";
  "10.1016/s0301-0511(96)05223-4" = "Hockey 1997";
  "10.1097/acm.0b013e3181b37b8f" = "LeBlanc 2009";
  "10.1080/02699930500270913" = "Kofman 2006";
  "10.1037/a0016980" = "Schoofs 2009";
  "10.1037/0033-2909.130.3.355" = "Dickerson 2004";
  "10.1108/md-02-2015-0063" = "Brueggen 2015";
  "10.1177/001872088903100503" = "Hancock 1989";
  "10.1108/s1534-0856(2012)0000015015" = "Moore & Tenney 2012";
  "10.19030/jabr.v21i1.1497" = "Margheim 2011";
  "10.1108/eb022805" = "Stuhlmacher 1998";
  "10.1111/j.1467-9280.1997.tb00460.x" = "Tice & Baumeister 1997";
  "10.3390/ijerph20065031" = "Sirois 2023";
  "10.1186/s12909-017-1091-0" = "Koetter 2017";
  "10.2224/sbp.2008.36.2.183" = "Vaez 2008";
  "10.1016/j.sbspro.2011.11.288" = "Elias 2011";
  "10.1159/000513781" = "Yoo 2020";
  "10.1111/j.1744-6570.2008.00113.x" = "Gilboa 2008";
  "10.1080/07448481.2010.510163" = "Pettit 2011";
  "10.1080/02673843.2019.1596823" = "Pascoe 2019"
}
$ok = 0; $fail = 0
foreach ($d in $dois.Keys) {
  $label = $dois[$d]
  $found = $false
  for ($t = 1; $t -le 2 -and -not $found; $t++) {
    try {
      $r = Invoke-RestMethod -Uri ("https://api.crossref.org/works/" + $d) -TimeoutSec 30
      $status = $r.message.status
      $title = ($r.message.title -join "") 
      if ($title.Length -gt 70) { $title = $title.Substring(0, 70) }
      Write-Output ("OK   {0,-32} status={1}  title={2}" -f $label, $status, $title)
      $ok++; $found = $true
    } catch {
      Start-Sleep -Seconds 3
    }
  }
  if (-not $found) {
    Write-Output ("FAIL {0,-32} no crossref record" -f $label)
    $fail++
  }
}
Write-Output ("RESULT: ok={0} fail={1}" -f $ok, $fail)
# 无 DOI 的文献用 OpenAlex ID 验证
foreach ($id in @("https://openalex.org/W2801232253")) {
  try {
    $r = Invoke-RestMethod -Uri $id -TimeoutSec 30
    Write-Output ("OK   {0,-32} title={1}" -f "openalex Pychyl 2000", $r.title)
  } catch { Write-Output ("FAIL openalex {0}" -f $id) }
}