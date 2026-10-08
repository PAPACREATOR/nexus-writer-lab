"""Preserve PID-filtered ETW events and pipe matches without claiming causality."""
import json
from pathlib import Path
import xml.etree.ElementTree as E

root = Path('lab-evidence')
pids = set()
for path in (root / 'A').glob('*-launches.json'):
    for launch in json.loads(path.read_text('utf-8')):
        pids.update(e['pid'] for e in launch.get('process_observation', {}).get('events', []))
ns = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
count = relevant = pipe = 0
with (root / 'target-etw-events.jsonl').open('w', encoding='utf-8') as target, (root / 'pipe-etw-events.jsonl').open('w', encoding='utf-8') as pipes:
    for _, event in E.iterparse(root / 'trace.xml', events=('end',)):
        if event.tag.rsplit('}', 1)[-1] != 'Event':
            continue
        count += 1
        serialized = E.tostring(event, encoding='unicode')
        execution = event.find('e:System/e:Execution', ns)
        pid = int(execution.get('ProcessID', '0')) if execution is not None else 0
        values = {item.get('Name', ''): item.text for item in event.findall('e:EventData/e:Data', ns)}
        record = {'pid': pid, 'data': values, 'xml': serialized}
        if pid in pids:
            relevant += 1
            target.write(json.dumps(record, ensure_ascii=False) + '\n')
        if 'namedpipe' in serialized.lower() or 'osl_pipe' in serialized.lower():
            pipe += 1
            pipes.write(json.dumps(record, ensure_ascii=False) + '\n')
        event.clear()
(root / 'trace-summary.json').write_text(json.dumps({'sampled_target_pids': sorted(pids),
    'total_etw_events': count, 'target_pid_events': relevant, 'pipe_matches_all_pids': pipe,
    'causal_classification': 'NOT PROVEN', 'note': 'Correlate PID, operation, result and timestamps. Circular trace and sampling may omit events.'}, indent=2), encoding='utf-8')
