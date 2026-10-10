# Adapted from lab/run-standard-user.ps1; common helper remains unchanged.
param([Parameter(Mandatory=$true)][string]$SandyExe)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable GitHub runner only' }
$source=(Get-Location).Path
$pythonRoot=& python -c 'import sys; print(sys.prefix)'
$officeRoot=Split-Path (Split-Path $env:LIBREOFFICE_EXE -Parent) -Parent
$name='NexusWriterMailLab'
$secret=[guid]::NewGuid().ToString('N')+'aA!9'
$secure=ConvertTo-SecureString $secret -AsPlainText -Force
$null=New-LocalUser -Name $name -Password $secure -Description 'Disposable Writer pipe experiment'
$users=Get-LocalGroup -SID 'S-1-5-32-545'
Add-LocalGroupMember -Group $users -Member $name
$credential=New-Object System.Management.Automation.PSCredential("$env:COMPUTERNAME\$name",$secure)
$output=Join-Path $source 'lab-evidence/sandy-standard-user-launch'
$null=New-Item -ItemType Directory -Path $output -Force
$arguments=@('-NoProfile','-File',('"'+(Join-Path $source 'lab/sandy-local-pipes/user-bootstrap.ps1')+'"'),'-SourceRoot',('"'+$source+'"'),'-PythonRoot',('"'+$pythonRoot+'"'),'-OfficeRoot',('"'+$officeRoot+'"'),'-SandyExe',('"'+$SandyExe+'"'),'-SourceCommit',$env:GITHUB_SHA)
try {
    $process=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -Credential $credential -LoadUserProfile -WindowStyle Hidden -ArgumentList $arguments -RedirectStandardOutput (Join-Path $output 'stdout.txt') -RedirectStandardError (Join-Path $output 'stderr.txt') -Wait -PassThru
    $labProfile=Get-CimInstance Win32_UserProfile | Where-Object {$_.SID -eq (Get-LocalUser -Name $name).SID.Value} | Select-Object -First 1
    if ($labProfile) {
        $evidence=Join-Path $labProfile.LocalPath 'NexusWriterLab/repo/lab-evidence'
        if (Test-Path -LiteralPath $evidence) { Copy-Item -LiteralPath $evidence -Destination (Join-Path $source 'lab-evidence/standard-user') -Recurse }
    }
    @{exit_code=$process.ExitCode;new_admin_membership=$false;production_changes=@()} | ConvertTo-Json | Set-Content (Join-Path $output 'result.json')
    Get-Content (Join-Path $output 'stdout.txt')
    if ($process.ExitCode -ne 0) { Get-Content (Join-Path $output 'stderr.txt'); throw 'Writer pipe experiment did not pass; preserve evidence' }
} finally {
    Remove-LocalUser -Name $name
    $secret=$null; $credential=$null; $secure=$null
}
