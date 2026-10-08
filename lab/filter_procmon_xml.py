import zipfile,re,pathlib,json,hashlib,time,sys
z=zipfile.ZipFile(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
targets={b'4420',b'6812',b'4580',b'7792',b'7868',b'7960'}
counts={'processes':0,'events':0}; digest=hashlib.sha256(); start=time.time(); buffer=b''
with z.open('procmon/writer.xml') as source, (out/'writer-stacks.xml').open('wb') as dest:
 dest.write(b'<?xml version="1.0" encoding="UTF-8"?><procmon>')
 while chunk:=source.read(4*1024*1024):
  digest.update(chunk); buffer+=chunk
  parts=re.split(rb'(</process>|</event>)',buffer)
  buffer=parts[-1]
  for i in range(0,len(parts)-1,2):
   body=parts[i]; kind=b'process' if parts[i+1]==b'</process>' else b'event'
   pos=body.find(b'<'+kind+b'>')
   if pos<0: continue
   block=body[pos:]+parts[i+1]
   pid=re.search(rb'<(?:ProcessId|PID)>(\d+)</(?:ProcessId|PID)>',block[:600])
   if pid and pid[1] in targets:
    dest.write(block); counts['processes' if kind==b'process' else 'events']+=1
 dest.write(b'</procmon>')
counts.update(xml_sha256=digest.hexdigest(),elapsed_seconds=round(time.time()-start,2),source_bytes=z.getinfo('procmon/writer.xml').file_size)
(out/'stack-filter.json').write_text(json.dumps(counts,indent=2)); print(counts)
