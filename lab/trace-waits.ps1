param([string]$Output,[string]$StopFile,[string]$WriterRoot)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class NexusWaitQuery {
 [DllImport("advapi32.dll", SetLastError=true)] static extern IntPtr OpenThreadWaitChainSession(uint flags, IntPtr callback);
 [DllImport("advapi32.dll", SetLastError=true)] static extern bool GetThreadWaitChain(IntPtr h, UIntPtr context, uint flags, uint tid, ref uint count, IntPtr nodes, out bool cycle);
 [DllImport("advapi32.dll")] static extern void CloseThreadWaitChainSession(IntPtr h);
 public static string Query(uint tid) {
  IntPtr h=OpenThreadWaitChainSession(0,IntPtr.Zero);
  if(h==IntPtr.Zero) return "session_error="+Marshal.GetLastWin32Error();
  IntPtr nodes=Marshal.AllocHGlobal(280*16);
  try {
   uint count=16; bool cycle;
   bool ok=GetThreadWaitChain(h,UIntPtr.Zero,0,tid,ref count,nodes,out cycle);
   if(!ok) return "query_error="+Marshal.GetLastWin32Error();
   string value="cycle="+cycle+";count="+count;
   for(int i=0;i<Math.Min(count,16);i++) {
    IntPtr n=IntPtr.Add(nodes,280*i); int type=Marshal.ReadInt32(n), status=Marshal.ReadInt32(n,4);
    value+=";type="+type+",status="+status;
    if(type==8) value+=",pid="+Marshal.ReadInt32(n,8)+",tid="+Marshal.ReadInt32(n,12)+",wait="+Marshal.ReadInt32(n,16);
    else value+=",object="+Marshal.PtrToStringUni(IntPtr.Add(n,8),128).TrimEnd('\0');
   }
   return value;
  } finally { Marshal.FreeHGlobal(nodes); CloseThreadWaitChainSession(h); }
 }
}
'@
$deadline=[DateTime]::UtcNow.AddMinutes(20)
while (-not (Test-Path -LiteralPath $StopFile) -and [DateTime]::UtcNow -lt $deadline) {
 foreach ($p in @(Get-Process -Name soffice,soffice.bin -ErrorAction SilentlyContinue)) {
  try {
   $path=$p.Path
   if (-not $path -or -not $path.StartsWith($WriterRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { continue }
   foreach ($thread in $p.Threads) {
    $row=@{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;tid=$thread.Id;image=$path;state=$thread.ThreadState.ToString()}
    try { if ($thread.ThreadState -eq 'Wait') { $row.wait_reason=$thread.WaitReason.ToString() } } catch { $row.wait_reason_error=$_.Exception.Message }
    try { $row.wait_chain=[NexusWaitQuery]::Query([uint32]$thread.Id) } catch { $row.wait_chain_error=$_.Exception.Message }
    $row | ConvertTo-Json -Compress | Add-Content -LiteralPath $Output -Encoding utf8
   }
  } catch { @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;query_error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content -LiteralPath $Output -Encoding utf8 }
 }
 Start-Sleep -Seconds 2
}
