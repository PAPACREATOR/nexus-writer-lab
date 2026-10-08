param([string]$SourceRoot,[string]$PythonRoot,[string]$OfficeRoot,[string]$Suite,[int]$Shard=0)
$ErrorActionPreference='Stop'
$target=Join-Path $env:USERPROFILE 'NexusWriterLab'
$null=New-Item -ItemType Directory -Path $target -Force
foreach ($pair in @(@($SourceRoot,(Join-Path $target 'repo')), @($PythonRoot,(Join-Path $target 'python')), @($OfficeRoot,(Join-Path $target 'office')))) {
    robocopy $pair[0] $pair[1] /E /NFL /NDL /NJH /NJS /NP /XD lab-evidence __pycache__ .pytest_cache | Out-Null
    if ($LASTEXITCODE -gt 7) { throw 'Cannot copy per-user test fixture' }
}
$python=Join-Path $target 'python/python.exe'
$env:LIBREOFFICE_EXE=Join-Path $target 'office/program/soffice.com'
$env:PYTHONUTF8='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
Set-Location -LiteralPath (Join-Path $target 'repo')
$null=New-Item -ItemType Directory -Path lab-evidence -Force
& $python -c "import ctypes as C,json,os; from ctypes import wintypes as W; a=C.WinDLL('advapi32'); k=C.WinDLL('kernel32'); k.GetCurrentProcess.restype=W.HANDLE; a.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]; a.GetTokenInformation.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)]; t=W.HANDLE(); e=W.DWORD(); n=W.DWORD(); assert a.OpenProcessToken(k.GetCurrentProcess(),8,C.byref(t)); assert a.GetTokenInformation(t,20,C.byref(e),4,C.byref(n)); d={'user':os.environ['USERNAME'],'profile':os.environ['USERPROFILE'],'elevated':bool(e.value)}; print(json.dumps(d)); open('lab-evidence/standard-user.json','w').write(json.dumps(d)); assert e.value==0, 'Elevated test process refused'"
if ($LASTEXITCODE -ne 0) { throw 'Standard-user token verification failed' }
& $python -c "import hashlib,json,os,pathlib; p=pathlib.Path(os.environ['LIBREOFFICE_EXE']).with_name('soffice.bin'); print(json.dumps({'binary':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))" > lab-evidence/standard-user-writer-hash.json
if ($Suite -eq 'routes') { & $python -m lab.run_case H }
elseif ($Suite -eq 'probe') { & $python -m lab.run_lok_probe }
else { & $python -m lab.run_candidate_suite $Suite $Shard }
exit $LASTEXITCODE
