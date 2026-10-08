import csv, io, json, zipfile, collections, pathlib, re, sys
z=zipfile.ZipFile(sys.argv[1])
out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
pids={4420,6812,4580,7792,7868,7960}
counts=collections.Counter(); results=collections.Counter(); rows=[]; total=0; first=last=None
with z.open('procmon/writer.csv') as raw:
 for r in csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline='')):
  total+=1; first=first or r['Time of Day']; last=r['Time of Day']
  if int(r['PID']) in pids or r['Process Name'].lower() in ('soffice.bin','soffice.com'):
   rows.append(r); counts[r['PID']]+=1; results[r['Result']]+=1
summary={'total_events':total,'first':first,'last':last,'expected_pids':sorted(pids),'pid_counts':dict(counts),'results':dict(results),'focused_events':len(rows),'run':37822420842,'artifact':11570414451}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(out/'writer-events.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for n in z.namelist():
 if n.startswith('standard-user/') and not '/tmp/' in n or n.startswith('procmon/') and not n.endswith(('.pml','.xml','.csv')):
  dest=out/n; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(z.read(n))
print(json.dumps(summary,indent=2))
print(json.dumps([r for r in rows if r['Result']!='SUCCESS'][:30],indent=2))
head=z.open('procmon/writer.xml').read(12000).decode('utf-8-sig',errors='replace')
print(re.sub(r'(?<=>)[^<]*(?=<)',lambda m:'{TEXT:'+str(len(m.group()))+'}',head)[:3000])
