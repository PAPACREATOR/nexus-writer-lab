param([string]$Suite='routes',[int]$Shard=0)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable GitHub runner only; never create this account on the user PC' }
$source=(Get-Location).Path
$pythonRoot=& python -c 'import sys; print(sys.prefix)'
$officeRoot=Split-Path (Split-Path $env:LIBREOFFICE_EXE -Parent) -Parent
$name='NexusWriterLab'
$secret=[guid]::NewGuid().ToString('N')+'aA!9'
$secure=ConvertTo-SecureString $secret -AsPlainText -Force
$null=New-LocalUser -Name $name -Password $secure -Description 'Disposable Writer laboratory user'
$users=Get-LocalGroup -SID 'S-1-5-32-545'
Add-LocalGroupMember -Group $users -Member $name
$credential=New-Object System.Management.Automation.PSCredential("$env:COMPUTERNAME\$name",$secure)
$output=Join-Path $source 'lab-evidence/standard-user-launch'
$null=New-Item -ItemType Directory -Path $output -Force
$arguments=@('-NoProfile','-File',('"'+(Join-Path $source 'lab/user-bootstrap.ps1')+'"'),'-SourceRoot',('"'+$source+'"'),'-PythonRoot',('"'+$pythonRoot+'"'),'-OfficeRoot',('"'+$officeRoot+'"'),'-Suite',$Suite,'-Shard',$Shard)
try {
    $process=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -Credential $credential -LoadUserProfile -WindowStyle Hidden -ArgumentList $arguments -RedirectStandardOutput (Join-Path $output 'stdout.txt') -RedirectStandardError (Join-Path $output 'stderr.txt') -Wait -PassThru
    $profile=Get-CimInstance Win32_UserProfile | Where-Object {$_.SID -eq (Get-LocalUser -Name $name).SID.Value} | Select-Object -First 1
    if ($profile) {
        $evidence=Join-Path $profile.LocalPath 'NexusWriterLab/repo/lab-evidence'
        if (Test-Path -LiteralPath $evidence) { Copy-Item -LiteralPath $evidence -Destination (Join-Path $source 'lab-evidence/standard-user') -Recurse }
    }
    @{suite=$Suite;shard=$Shard;exit_code=$process.ExitCode;new_admin_membership=$false;production_changes=@()} | ConvertTo-Json | Set-Content (Join-Path $output 'result.json')
    if ($process.ExitCode -ne 0) { Get-Content (Join-Path $output 'stderr.txt'); throw 'Standard-user validation failed; preserve evidence' }
} finally {
    Remove-LocalUser -Name $name
    $secret=$null; $credential=$null; $secure=$null
}
