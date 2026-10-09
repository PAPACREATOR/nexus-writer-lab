param([Parameter(Mandatory=$true)][datetime]$Since,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable runner event metadata only' }
$result=@{schema='nexus.writer.crash-event-metadata.v1';since_utc=$Since.ToUniversalTime().ToString('o');status='queried';events=@();memory_dump=$false;process_attach=$false;raw_event_messages_saved=$false}
$fields=@('AppName','AppVersion','ModuleName','ModuleVersion','ExceptionCode','FaultingOffset','ProcessId','ProcessCreationTime','AppPath','ModulePath')
try {
    $events=Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Application Error';Id=1000;StartTime=$Since} -MaxEvents 256 -ErrorAction Stop
    foreach($event in $events) {
        [xml]$xml=$event.ToXml()
        $data=@{}
        foreach($item in $xml.Event.EventData.Data) { if($item.Name) { $data[[string]$item.Name]=[string]$item.'#text' } }
        # Only the disposable fixture's own Python/Writer crashes are retained.
        if(-not $data.AppPath -or -not $data.AppPath.StartsWith('C:\Users\NexusWriterLab\NexusWriterLab\',[StringComparison]::OrdinalIgnoreCase)) { continue }
        if($data.AppName -notin @('python.exe','soffice.bin','soffice.exe','soffice.com')) { continue }
        $row=@{event_id=1000;record_id=$event.RecordId;time_utc=$event.TimeCreated.ToUniversalTime().ToString('o')}
        foreach($field in $fields) { if($data.ContainsKey($field)) { $row[$field]=$data[$field].Substring(0,[Math]::Min(1024,$data[$field].Length)) } }
        $result.events+=@($row)
    }
} catch {
    $result.status='query_empty_or_unavailable'
    $result.reader_error=$_.Exception.Message.Substring(0,[Math]::Min(1024,$_.Exception.Message.Length))
}
$result.event_count=$result.events.Count
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Output -Encoding UTF8
Write-Output ('Fixture crash metadata events='+$result.event_count+'; no memory or dump captured')
