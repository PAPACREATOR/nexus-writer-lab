# Recorder runs on an ephemeral CI host; Writer stays in the unchanged LPAC/Job.
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Path lab-evidence -Force | Out-Null
Get-Command procmon*,cdb* -ErrorAction SilentlyContinue | Select-Object Name,Source | ConvertTo-Json | Out-File lab-evidence/trace-tool-inventory.json
wevtutil gp Microsoft-Windows-Kernel-File /ge:true /gm:true > lab-evidence/kernel-file-provider.txt
wevtutil gp Microsoft-Windows-Kernel-Process /ge:true /gm:true > lab-evidence/kernel-process-provider.txt
@('Microsoft-Windows-Kernel-File 0xffffffffffffffff 5', 'Microsoft-Windows-Kernel-Process 0x10 5') | Set-Content lab-evidence/providers.txt
logman create trace NexusWriterLab -o lab-evidence/writer.etl -f bincirc -max 128 -pf lab-evidence/providers.txt -bs 64 -nb 16 128 -ets *> lab-evidence/etw-start.txt
$started = $LASTEXITCODE -eq 0
@{started=$started; recorder='ETW'; max_mb=128; circular=$true; writer_security_changes=@()} | ConvertTo-Json | Out-File lab-evidence/trace-settings.json
try {
    python -m lab.run_case A
    $testCode = $LASTEXITCODE
} finally {
    if ($started) {
        logman query NexusWriterLab -ets *> lab-evidence/etw-session-status.txt
        logman stop NexusWriterLab -ets *> lab-evidence/etw-stop.txt
        $trace = Get-ChildItem lab-evidence -Filter '*.etl' | Select-Object -First 1
        if ($trace) {
            tracerpt $trace.FullName -o lab-evidence/trace.xml -of XML -lr -summary lab-evidence/etw-summary.txt -report lab-evidence/etw-report.xml -y *> lab-evidence/tracerpt-console.txt
            python -m lab.summarize_trace
        }
    }
}
exit $testCode
