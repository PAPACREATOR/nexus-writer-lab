param(
 [Parameter(Mandatory=$true)][int]$TargetPid,
 [Parameter(Mandatory=$true)][long]$TargetHwnd,
 [Parameter(Mandatory=$true)][string]$Output,
 [ValidateSet('Both','UIA','MSAA')][string]$Reader='Both'
)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
# The parent bounds this helper to 3 s and terminates only this helper on timeout.
# Persist stages so a timeout remains distinct from an empty provider tree.
$result=@{schema=2;pid=$TargetPid;hwnd=('0x{0:x}' -f $TargetHwnd);reader=$Reader;stage='guard';completed=$false;interaction=$false;memory_dump=$false;document_payload=$false;non_atomic_observation=$true;uia=@{status='not_run'};msaa=@{status='not_run'}}
function Save-Result {
 $result.utc=[DateTime]::UtcNow.ToString('o')
 $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Output -Encoding utf8
}
try {
 $target=Get-Process -Id $TargetPid
 if (-not $target.Path.StartsWith('C:\Users\NexusWriterLab\NexusWriterLab\office\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Not the synthetic Writer fixture' }
 if ($TargetHwnd -eq 0) { throw 'A nonzero verified Writer HWND is required' }
 Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class NexusDialogWindowGuard {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowTextW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 public static string ClassName(IntPtr h) { var s=new StringBuilder(256); GetClassNameW(h,s,s.Capacity); return s.ToString(); }
 public static string Caption(IntPtr h) { var s=new StringBuilder(512); GetWindowTextW(h,s,s.Capacity); return s.ToString(); }
}
'@
 $hwnd=[IntPtr]$TargetHwnd
 [uint32]$owner=0
 $thread=[NexusDialogWindowGuard]::GetWindowThreadProcessId($hwnd,[ref]$owner)
 if ($thread -eq 0 -or $owner -ne $TargetPid) { throw 'HWND owner does not match the verified synthetic Writer PID' }
 $nativeClass=[NexusDialogWindowGuard]::ClassName($hwnd)
 $caption=[NexusDialogWindowGuard]::Caption($hwnd)
 if ($nativeClass -ne 'SALFRAME' -or $caption -ne 'LibreOffice 26.2' -or -not [NexusDialogWindowGuard]::IsWindowVisible($hwnd)) { throw 'HWND is not the visible synthetic startup SALFRAME' }
 $result.window=@{native_class=$nativeClass;native_caption=$caption;owner_pid=$owner;thread_id=$thread;image=$target.Path}
 $result.stage='guard_passed'
 Save-Result

 if ($Reader -ne 'MSAA') {
  $result.stage='uia_query'
  $result.uia=@{status='in_progress';root=$null;descendant_count=$null;saved_count=0;truncated=$false;nodes=@();errors=@()}
  Save-Result
  try {
   Add-Type -AssemblyName UIAutomationClient
   Add-Type -AssemblyName UIAutomationTypes
   function Read-UiaProperties($element) {
    $current=$element.Current
    # Property getters only. No patterns, values, text ranges or actions.
    @{name=$current.Name;class=$current.ClassName;type=$current.ControlType.ProgrammaticName;automation_id=$current.AutomationId;native_hwnd=$current.NativeWindowHandle;process_id=$current.ProcessId;is_control=$current.IsControlElement;is_content=$current.IsContentElement;is_enabled=$current.IsEnabled;is_offscreen=$current.IsOffscreen}
   }
   function Test-UiaDocumentScope($element,$root) {
    $cursor=$element
    for($depth=0;$depth -lt 16 -and $null -ne $cursor;$depth++) {
     if($cursor.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document) { return $true }
     if($cursor.Equals($root)) { return $false }
     $cursor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($cursor)
    }
    # Unknown ancestry is excluded rather than risking a document subtree.
    return $true
   }
   $window=[System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
   if ($null -eq $window) { throw 'UIA FromHandle returned null' }
   if ($window.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document) { throw 'UIA root unexpectedly identifies a document' }
   $result.uia.root=Read-UiaProperties $window
   Save-Result
   # TrueCondition is raw view. Keep every control type and report counts.
   $nodes=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
   $result.uia.descendant_count=$nodes.Count
   $result.uia.truncated=($nodes.Count -gt 128)
   $saved=@()
   for($i=0;$i -lt [Math]::Min($nodes.Count,128);$i++) {
    try {
     if(Test-UiaDocumentScope $nodes[$i] $window) {
      $saved+=@{index=$i;type=$nodes[$i].Current.ControlType.ProgrammaticName;payload_skipped=$true;reason='document_or_unverified_ancestry'}
     } else {
      $properties=Read-UiaProperties $nodes[$i]
      $properties.index=$i
      $saved+=$properties
     }
    } catch { $result.uia.errors+=@{index=$i;error=$_.Exception.Message} }
   }
   $result.uia.nodes=$saved
   $result.uia.saved_count=$saved.Count
   $result.uia.status='completed'
  } catch { $result.uia.status='error'; $result.uia.errors+=@{error=$_.Exception.Message} }
  $result.stage='uia_finished'
  Save-Result
 }

 if ($Reader -ne 'UIA') {
  $result.stage='msaa_query'
  $result.msaa=@{status='in_progress'}
  Save-Result
  try {
   Add-Type -AssemblyName Accessibility
   $accessibilityAssembly=[Accessibility.IAccessible].Assembly.Location
   Add-Type -ReferencedAssemblies $accessibilityAssembly @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using Accessibility;
public static class NexusDialogMsaa {
 public sealed class Node { public string path; public string role; public string name; public int? child_count; public bool payload_skipped; public List<string> errors=new List<string>(); }
 public sealed class Result { public string status="in_progress"; public int? hresult; public int com_initialization_hresult; public string com_initialization_hresult_hex; public string com_apartment; public bool com_uninitialize_called; public bool truncated; public List<Node> nodes=new List<Node>(); public List<string> errors=new List<string>(); }
 [DllImport("ole32.dll")] static extern int CoInitializeEx(IntPtr reserved,uint model);
 [DllImport("ole32.dll")] static extern void CoUninitialize();
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out IAccessible value);
 [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible parent,int first,int count,[Out,MarshalAs(UnmanagedType.LPArray,ArraySubType=UnmanagedType.Struct,SizeParamIndex=2)] object[] children,out int obtained);
 static Node Read(IAccessible acc,object child,string path) {
  var n=new Node{path=path};
  try { n.role=Convert.ToString(acc.get_accRole(child),CultureInfo.InvariantCulture); } catch(Exception e) { n.errors.Add("role: "+e.Message); }
  // ROLE_SYSTEM_DOCUMENT=15: do not collect its Name or content.
  n.payload_skipped=n.role=="15";
  if(!n.payload_skipped) try { n.name=acc.get_accName(child); } catch(Exception e) { n.errors.Add("name: "+e.Message); }
  return n;
 }
 static void Walk(IAccessible acc,string path,int depth,Result output) {
  if(output.nodes.Count>=128 || depth>8) { output.truncated=true; return; }
  var n=Read(acc,0,path); output.nodes.Add(n);
  if(n.payload_skipped) return;
  int count;
  try { count=acc.accChildCount; n.child_count=count; } catch(Exception e) { n.errors.Add("child_count: "+e.Message); return; }
  if(count<=0) return;
  int request=Math.Min(count,128-output.nodes.Count);
  if(request<count) output.truncated=true;
  if(request<=0) return;
  var children=new object[request]; int obtained;
  int hr=AccessibleChildren(acc,0,request,children,out obtained);
  if(hr<0) { n.errors.Add("AccessibleChildren HRESULT 0x"+hr.ToString("x8")); return; }
  for(int i=0;i<obtained;i++) {
   if(output.nodes.Count>=128) { output.truncated=true; break; }
   object child=children[i]; var accessible=child as IAccessible;
   if(accessible!=null) {
    try { Walk(accessible,path+"/"+i,depth+1,output); }
    catch(Exception e) { output.errors.Add(path+"/"+i+": "+e.Message); }
    finally { if(Marshal.IsComObject(accessible)) Marshal.ReleaseComObject(accessible); }
   } else if(child is int) { output.nodes.Add(Read(acc,child,path+"/"+i)); }
   else { output.errors.Add(path+"/"+i+": unsupported child VARIANT"); }
  }
 }
 public static Result Query(IntPtr h) {
  var result=new Result(); IAccessible root=null; bool balanceCom=false;
  try {
   // Initialize only this external reader thread. An existing apartment stays
   // in its current mode; S_OK and S_FALSE each require one balanced release.
   int comHr=CoInitializeEx(IntPtr.Zero,2); // COINIT_APARTMENTTHREADED
   result.com_initialization_hresult=comHr;
   result.com_initialization_hresult_hex="0x"+comHr.ToString("x8");
   balanceCom=comHr==0 || comHr==1;
   if(balanceCom) result.com_apartment="STA";
   else if(comHr==unchecked((int)0x80010106)) result.com_apartment="existing_apartment_kept"; // RPC_E_CHANGED_MODE
   else { result.status="com_initialization_error"; return result; }
   Guid iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
   result.hresult=AccessibleObjectFromWindow(h,unchecked((uint)-4),ref iid,out root);
   if(result.hresult<0 || root==null) { result.status="unavailable"; return result; }
   Walk(root,"root",0,result); result.status="completed";
  } catch(Exception e) { result.status="error"; result.errors.Add(e.Message); }
  finally {
   try { if(root!=null && Marshal.IsComObject(root)) Marshal.ReleaseComObject(root); }
   finally { if(balanceCom) { CoUninitialize(); result.com_uninitialize_called=true; } }
  }
  return result;
 }
}
'@
   # MSAA properties/child enumeration only: no default action/select/value.
   $result.msaa=[NexusDialogMsaa]::Query($hwnd)
  } catch { $result.msaa=@{status='error';error=$_.Exception.Message} }
  $result.stage='msaa_finished'
  Save-Result
 }
 $result.stage='finished'
 $result.completed=$true
 Save-Result
} catch {
 $result.stage='error'
 $result.error=$_.Exception.Message
 Save-Result
}
