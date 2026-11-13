"""Narrow manually selected provenance anchors; no changes to existing grades."""
import json
from pathlib import Path
p=Path('finding_anchors.json');a=json.loads(p.read_text());a['flags']['M1']='KeyError';a['resets']['C1']='purpose';a['metering']['C2']='overwrit|tenant trust';a['cron']['M2']='never raises|Outcome|invoke[^\\n]{0,60}wrong';a['carts']['M1']='Expired coupons|expiry validation';a['invites']['C2']='re.charges|Retry safety|retried accept|retry.*billing';a['migrations']['C1']='lost.update|overwrit|stale backfill';a['search']['M1']='37,500|10.4|10 hours|rebuild throughput';p.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
