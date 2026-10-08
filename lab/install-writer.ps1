$ErrorActionPreference = 'Stop'
$url = 'https://downloadarchive.documentfoundation.org/libreoffice/old/26.2.6.2/win/x86_64/LibreOffice_26.2.6.2_Win_x86-64.msi'
$msi = Join-Path $env:RUNNER_TEMP 'LibreOffice_26.2.6.2_Win_x86-64.msi'
Invoke-WebRequest $url -OutFile $msi
if ((Get-FileHash $msi -Algorithm SHA256).Hash.ToLowerInvariant() -ne '788ce7d4b56460357f57552cb8cd848e8f2254f28f6e51fa61e0c65a18096373') { throw 'Official archive hash mismatch' }
$install = Start-Process msiexec.exe -ArgumentList @('/i', $msi, '/qn', '/norestart') -WindowStyle Hidden -Wait -PassThru
if ($install.ExitCode -notin @(0,3010)) { throw "MSI failed: $($install.ExitCode)" }
$exe = 'C:\Program Files\LibreOffice\program\soffice.com'
New-Item -ItemType Directory -Path lab-evidence -Force | Out-Null
& $exe --version | Out-File lab-evidence/libreoffice-version.txt
if ((Get-Content lab-evidence/libreoffice-version.txt -Raw) -notmatch '26\.2\.6\.2') { throw 'Wrong Writer build' }
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsName,OsVersion,OsBuildNumber | ConvertTo-Json | Out-File lab-evidence/windows-version.json
Get-FileHash 'C:\Program Files\LibreOffice\program\soffice.bin' | ConvertTo-Json | Out-File lab-evidence/writer-binary-hash.json
"LIBREOFFICE_EXE=$exe" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
