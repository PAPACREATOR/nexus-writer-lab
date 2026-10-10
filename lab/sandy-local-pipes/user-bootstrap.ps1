# Adapted from lab/user-bootstrap.ps1; no dispatch to candidate/LibreOfficeKit.
param([string]$SourceRoot,[string]$PythonRoot,[string]$OfficeRoot,[string]$SandyExe,[string]$SourceCommit)
$ErrorActionPreference='Stop'
$identity=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$sid=$identity.User.Value
$profileEntry=Get-ItemProperty -LiteralPath ('HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\'+$sid)
$labProfileDirectory=[Environment]::ExpandEnvironmentVariables($profileEntry.ProfileImagePath)
$env:USERPROFILE=$labProfileDirectory
$env:USERNAME=($identity.Name -split '\\')[-1]
$env:USERDOMAIN=$env:COMPUTERNAME
$env:APPDATA=Join-Path $labProfileDirectory 'AppData/Roaming'
$env:LOCALAPPDATA=Join-Path $labProfileDirectory 'AppData/Local'
$target=Join-Path $labProfileDirectory 'NexusWriterLab'
$null=New-Item -ItemType Directory -Path $target -Force
foreach ($pair in @(@($SourceRoot,(Join-Path $target 'repo')), @($PythonRoot,(Join-Path $target 'python')), @($OfficeRoot,(Join-Path $target 'office')))) {
    robocopy $pair[0] $pair[1] /E /NFL /NDL /NJH /NJS /NP /XD lab-evidence __pycache__ .pytest_cache .git | Out-Null
    if ($LASTEXITCODE -gt 7) { throw 'Cannot copy per-user experiment fixture' }
}
$tools=Join-Path $target 'tools'
$null=New-Item -ItemType Directory -Path $tools -Force
Copy-Item -LiteralPath $SandyExe -Destination (Join-Path $tools 'sandy.exe')
$python=Join-Path $target 'python/python.exe'
$env:PYTHONUTF8='1'
$env:LAB_SOURCE_COMMIT=$SourceCommit
Set-Location -LiteralPath (Join-Path $target 'repo')
$null=New-Item -ItemType Directory -Path lab-evidence -Force
& $python -m lab.hash_office_tree --source $OfficeRoot --copy (Join-Path $target 'office') --output lab-evidence/runtime-tree-identity.json
if ($LASTEXITCODE -ne 0) { throw 'Per-user runtime copy failed exact identity verification' }
& $python -u lab/sandy-local-pipes/compare.py --sandy (Join-Path $tools 'sandy.exe') --libreoffice (Join-Path $target 'office') --scratch (Join-Path $target 'sandy-local-pipes') --evidence (Join-Path $target 'repo/lab-evidence/sandy-local-pipes')
exit $LASTEXITCODE
