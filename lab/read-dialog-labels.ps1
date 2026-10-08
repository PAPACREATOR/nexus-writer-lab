param([int]$TargetPid,[string]$Output)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
try {
 $target=Get-Process -Id $TargetPid
 if (-not $target.Path.StartsWith('C:\Users\NexusWriterLab\NexusWriterLab\office\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Not the synthetic Writer fixture' }
 Add-Type -AssemblyName UIAutomationClient
 Add-Type -AssemblyName UIAutomationTypes
 # Read only labels of the visible SALFRAME belonging to this synthetic Writer PID.
 # No patterns/actions, no document reads, no memory dump, no accessibility setting changes.
 $condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$TargetPid)
 $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
 $labels=@()
 foreach($window in $windows) {
  if($window.Current.ClassName -ne 'SALFRAME' -or $window.Current.Name -ne 'LibreOffice 26.2') { continue }
  $nodes=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
  foreach($node in $nodes) {
   $current=$node.Current
   if($current.ControlType -eq [System.Windows.Automation.ControlType]::Text -or $current.ControlType -eq [System.Windows.Automation.ControlType]::Button) {
    $labels+=@{name=$current.Name;type=$current.ControlType.ProgrammaticName;class=$current.ClassName}
   }
  }
 }
 @{pid=$TargetPid;labels=$labels;interaction=$false;memory_dump=$false;document_payload=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Output
} catch { @{pid=$TargetPid;error=$_.Exception.Message;interaction=$false;memory_dump=$false} | ConvertTo-Json | Set-Content -LiteralPath $Output }
