"""Sanitize retained provenance excerpts; raw transcripts remain in their sources."""
import json,re
from pathlib import Path
p=Path('finding-provenance.json');d=json.loads(p.read_text())
for x in d:
 if x['excerpt']:
  x['excerpt']=re.sub(r'/(?:tmp|mnt|home)/[^\s`\)\]<>]*', '[local path omitted]',x['excerpt'])
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
