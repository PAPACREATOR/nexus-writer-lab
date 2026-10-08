$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$output=Join-Path $PWD 'lab-evidence/dump-tools'
$null=New-Item -ItemType Directory -Path $output -Force
$archive=Join-Path $env:RUNNER_TEMP 'Procdump.zip'
Invoke-WebRequest -Uri 'https://download.sysinternals.com/files/Procdump.zip' -OutFile $archive
$tools=Join-Path $env:RUNNER_TEMP 'nexus-procdump'
Expand-Archive -LiteralPath $archive -DestinationPath $tools
$dump=Join-Path $tools 'procdump64.exe'
function Confirm-MicrosoftBinary([string]$Path) {
 $signature=Get-AuthenticodeSignature -LiteralPath $Path
 @{path=$Path;status=$signature.Status.ToString();subject=$signature.SignerCertificate.Subject;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash} | ConvertTo-Json | Add-Content (Join-Path $output 'signatures.jsonl')
 if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') { throw 'Non-Microsoft or invalid signature refused' }
}
Confirm-MicrosoftBinary $dump
$cdb='C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'
if (-not (Test-Path -LiteralPath $cdb)) {
 $sdk=Join-Path $env:RUNNER_TEMP 'winsdksetup.exe'
 Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/?linkid=2382321' -OutFile $sdk
 Confirm-MicrosoftBinary $sdk
 $installer=Start-Process -FilePath $sdk -ArgumentList @('/features','OptionId.WindowsDesktopDebuggers','/quiet','/norestart') -WindowStyle Hidden -PassThru
 if (-not $installer.WaitForExit(600000)) { $installer.Kill(); throw 'Debugger installation timeout; no Writer launch' }
 @{exit_code=$installer.ExitCode;feature='OptionId.WindowsDesktopDebuggers';source='https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads'} | ConvertTo-Json | Set-Content (Join-Path $output 'sdk-install.json')
 if ($installer.ExitCode -notin @(0,3010)) { throw 'Debugger installation failed; preserve result' }
}
if (-not (Test-Path -LiteralPath $cdb)) { throw 'Offline debugger unavailable' }
Confirm-MicrosoftBinary $cdb
'LAB_PROCDUMP_EXE='+$dump | Out-File $env:GITHUB_ENV -Append -Encoding utf8
'LAB_CDB_EXE='+$cdb | Out-File $env:GITHUB_ENV -Append -Encoding utf8
