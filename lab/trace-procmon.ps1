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
$null=Start-Process -FilePath $exe -ArgumentList '/WaitForIdle' -WindowStyle Hidden -Wait
$baseline='NOT RUN'
try {
    ./lab/run-standard-user.ps1 -Suite baseline
    $baseline='PASS'
} catch {
    $baseline='FAIL'
    $_ | Out-String | Set-Content (Join-Path $output 'baseline-error.txt')
} finally {
    $null=Start-Process -FilePath $exe -ArgumentList '/Terminate' -WindowStyle Hidden -Wait
}
@{started_utc=$started;stopped_utc=[DateTime]::UtcNow.ToString('o');timezone=(Get-TimeZone).Id;baseline_workflow_result=$baseline;recorder_pid=$controller.Id;writer_timeout_seconds=45;writer_standard_user_required=$true;security_changes=@()} | ConvertTo-Json | Set-Content (Join-Path $output 'trace-context.json')
if (-not (Test-Path -LiteralPath $pml)) { throw 'Recorder did not produce native trace' }
$csv=Join-Path $output 'writer.csv'
$export=Start-Process -FilePath $exe -ArgumentList @('/Quiet','/OpenLog',('"'+$pml+'"'),'/SaveAs',('"'+$csv+'"')) -WindowStyle Hidden -Wait -PassThru
@{exit_code=$export.ExitCode;csv_exists=(Test-Path -LiteralPath $csv)} | ConvertTo-Json | Set-Content (Join-Path $output 'export.json')
$xml=Join-Path $output 'writer.xml'
$export=Start-Process -FilePath $exe -ArgumentList @('/Quiet','/OpenLog',('"'+$pml+'"'),'/SaveAs1',('"'+$xml+'"')) -WindowStyle Hidden -Wait -PassThru
@{exit_code=$export.ExitCode;xml_exists=(Test-Path -LiteralPath $xml);stacks_requested=$true;symbols_requested=$false} | ConvertTo-Json | Set-Content (Join-Path $output 'stack-export.json')
if ($baseline -ne 'PASS') { throw 'Baseline FAIL retained; recorder evidence must be reviewed separately' }
