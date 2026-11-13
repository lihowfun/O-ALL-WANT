"""Display the provenance excerpts for manual audit."""
import json
for x in json.load(open('finding-provenance.json')):print(x['cell'],x['case'],x['defect'],x['excerpt'])
