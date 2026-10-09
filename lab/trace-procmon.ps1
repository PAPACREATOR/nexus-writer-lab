param([ValidateSet('separate','python-read-root')][string]$OfficeLayout='separate')
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$output=Join-Path $PWD 'lab-evidence/procmon'
$null=New-Item -ItemType Directory -Path $output -Force
$archive=Join-Path $env:RUNNER_TEMP 'ProcessMonitor.zip'
Invoke-WebRequest -Uri 'https://download.sysinternals.com/files/ProcessMonitor.zip' -OutFile $archive
Get-FileHash -LiteralPath $archive -Algorithm SHA256 | ConvertTo-Json | Set-Content (Join-Path $output 'download-hash.json')
$tools=Join-Path $env:RUNNER_TEMP 'nexus-procmon'
Expand-Archive -LiteralPath $archive -DestinationPath $tools
$exe=Join-Path $tools 'Procmon64.exe'
$signature=Get-AuthenticodeSignature -LiteralPath $exe
@{status=$signature.Status.ToString();subject=$signature.SignerCertificate.Subject;sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash} | ConvertTo-Json | Set-Content (Join-Path $output 'binary-provenance.json')
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') { throw 'Unsigned/non-Microsoft recorder refused' }
if (Get-Process -Name Procmon,Procmon64 -ErrorAction SilentlyContinue) { throw 'Refusing to stop an existing recorder' }
$pml=Join-Path $output 'writer.pml'
$started=[DateTime]::UtcNow.ToString('o')
$controller=Start-Process -FilePath $exe -ArgumentList @('/AcceptEula','/Quiet','/Minimized','/BackingFile',('"'+$pml+'"'),'/Runtime','600') -WindowStyle Hidden -PassThru
Write-Output ('TRACE_STAGE=recorder_started UTC='+[DateTime]::UtcNow.ToString('o'))
function Invoke-RecorderBounded {
    param([string[]]$Arguments,[string]$Name,[int]$Seconds=120)
    Write-Host ('TRACE_STAGE='+$Name+' UTC='+[DateTime]::UtcNow.ToString('o'))
    $helper=Start-Process -FilePath $exe -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    $finished=$helper.WaitForExit($Seconds*1000)
    if (-not $finished) { $helper.Kill(); $helper.WaitForExit(5000) | Out-Null }
    @{stage=$Name;finished=$finished;exit_code=$(if ($finished) {$helper.ExitCode} else {$null})} | ConvertTo-Json | Set-Content (Join-Path $output ($Name+'-process.json'))
    return $finished
}
$ready=Invoke-RecorderBounded -Arguments @('/WaitForIdle') -Name 'wait_for_idle' -Seconds 30
if (-not $ready) {
    Invoke-RecorderBounded -Arguments @('/Terminate') -Name 'failed_start_stop' -Seconds 15 | Out-Null
    throw 'Recorder readiness not confirmed; no Writer run or policy bypass'
}
$baseline='NOT RUN'
try {
    Write-Output ('TRACE_STAGE=standard_user_baseline UTC='+[DateTime]::UtcNow.ToString('o'))
    ./lab/run-standard-user.ps1 -Suite baseline -OfficeLayout $OfficeLayout
    $baseline='PASS'
} catch {
    $baseline='FAIL'
    $_ | Out-String | Set-Content (Join-Path $output 'baseline-error.txt')
} finally {
    Invoke-RecorderBounded -Arguments @('/Terminate') -Name 'stop' -Seconds 30 | Out-Null
    $controller.WaitForExit(30000) | Out-Null
}
@{started_utc=$started;stopped_utc=[DateTime]::UtcNow.ToString('o');timezone=(Get-TimeZone).Id;baseline_workflow_result=$baseline;office_layout=$OfficeLayout;recorder_pid=$controller.Id;writer_timeout_seconds=45;writer_standard_user_required=$true;security_changes=@()} | ConvertTo-Json | Set-Content (Join-Path $output 'trace-context.json')
if (-not (Test-Path -LiteralPath $pml)) { throw 'Recorder did not produce native trace' }
$csv=Join-Path $output 'writer.csv'
$finished=Invoke-RecorderBounded -Arguments @('/Quiet','/OpenLog',('"'+$pml+'"'),'/SaveAs',('"'+$csv+'"')) -Name 'csv_export'
@{finished=$finished;csv_exists=(Test-Path -LiteralPath $csv)} | ConvertTo-Json | Set-Content (Join-Path $output 'export.json')
$xml=Join-Path $output 'writer.xml'
$finished=Invoke-RecorderBounded -Arguments @('/Quiet','/OpenLog',('"'+$pml+'"'),'/SaveAs1',('"'+$xml+'"')) -Name 'xml_export'
@{finished=$finished;xml_exists=(Test-Path -LiteralPath $xml);stacks_requested=$true;symbols_requested=$false} | ConvertTo-Json | Set-Content (Join-Path $output 'stack-export.json')
if ($baseline -ne 'PASS') { throw 'Baseline FAIL retained; recorder evidence must be reviewed separately' }
