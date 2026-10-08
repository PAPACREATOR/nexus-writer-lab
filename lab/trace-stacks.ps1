param([string]$Output,[string]$StopFile,[string]$WriterRoot,[string]$Debugger)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
# Read only captions/classes of the filtered foreign Writer PID. No WM_GETTEXT.
Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class NexusWindowCaption {
 public class Entry { public uint pid; public string title; public string windowClass; public bool visible; public bool child; }
 delegate bool EnumProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb,IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h,EnumProc cb,IntPtr p);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 public static List<Entry> Query(uint target) {
  var entries=new List<Entry>();
  Action<IntPtr,bool> read=(h,child)=>{uint pid;GetWindowThreadProcessId(h,out pid);if(pid!=target)return;
   var title=new StringBuilder(4096);var cls=new StringBuilder(256);GetWindowTextW(h,title,title.Capacity);GetClassNameW(h,cls,cls.Capacity);
   entries.Add(new Entry{pid=pid,title=title.ToString(),windowClass=cls.ToString(),visible=IsWindowVisible(h),child=child});};
  EnumWindows((h,p)=>{uint pid;GetWindowThreadProcessId(h,out pid);if(pid==target){read(h,false);EnumChildWindows(h,(c,x)=>{read(c,true);return true;},IntPtr.Zero);}return true;},IntPtr.Zero);
  return entries;
 }
}
'@
$null=New-Item -ItemType Directory -Path $Output -Force
$symbols=Join-Path $env:RUNNER_TEMP 'nexus-empty-symbols'
$null=New-Item -ItemType Directory -Path $symbols -Force
$commands=Join-Path $Output 'commands.txt'
@('~* k','lm','q') | Set-Content -LiteralPath $commands -Encoding ascii
$seen=@{}
$deadline=[DateTime]::UtcNow.AddMinutes(20)
while (-not (Test-Path -LiteralPath $StopFile) -and [DateTime]::UtcNow -lt $deadline) {
 foreach ($p in @(Get-Process -Name soffice,soffice.bin,soffice.com -ErrorAction SilentlyContinue)) {
  try {
   $path=$p.Path
   if (-not $path -or -not $path.StartsWith($WriterRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { continue }
   $age=([DateTime]::Now-$p.StartTime).TotalSeconds
   foreach ($threshold in @(10,25)) {
    $key=([string]$p.Id)+'-'+$threshold
    if ($age -lt $threshold -or $seen.ContainsKey($key)) { continue }
    $seen[$key]=$true
    @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;threshold_seconds=$threshold;image=$path;windows=@([NexusWindowCaption]::Query([uint32]$p.Id));payload='window captions/classes only';interaction=$false;memory_dump=$false} | ConvertTo-Json -Depth 5 -Compress | Add-Content (Join-Path $Output 'windows.jsonl')
    $log=Join-Path $Output ($key+'.stacks.txt')
    $start=[DateTime]::UtcNow
    # Non-invasive, non-suspending read. Stack-only text; no .dump or memory display.
    $helper=Start-Process -FilePath $Debugger -ArgumentList @('-pvr','-noshell','-nosqm','-y',('"'+$symbols+'"'),'-logo',('"'+$log+'"'),'-c','"~* k; lm; q"','-p',([string]$p.Id)) -WindowStyle Hidden -PassThru -RedirectStandardOutput ($log+'.stdout.txt') -RedirectStandardError ($log+'.stderr.txt')
    $heldHandle=$helper.Handle
    $finished=$helper.WaitForExit(8000)
    if (-not $finished) { $helper.Kill() }
    $helper.Refresh()
    @{utc=$start.ToString('o');pid=$p.Id;image=$path;age_seconds=$age;threshold_seconds=$threshold;finished=$finished;duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;exit_code=$(if ($finished) {$helper.ExitCode} else {$null});mode='non-invasive non-suspending -pvr';payload='stack frames and module list text only';memory_dump=$false;clone=$false;runtime_changes=@();non_atomic_observation=$true} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'capture.jsonl')
   }
  } catch { @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'errors.jsonl') }
 }
 Start-Sleep -Seconds 1
}
