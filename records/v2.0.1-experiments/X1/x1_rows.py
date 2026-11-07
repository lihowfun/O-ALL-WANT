"""Derived rows for the record and for blind grading: local paths and account names are replaced, and a path into
an arm's copy becomes repo-relative, so neither a reader nor a grader learns the arm from a path.

    python3 x1_rows.py <scratch rows.jsonl> <scratch dir> <label> <out rows.jsonl>
"""
import json
import os
import re
import sys


def main(src, scratch, label, out):
    scratch = os.path.realpath(scratch)
    home = os.path.expanduser("~")
    user = os.path.basename(home)
    with open(out, "w", encoding="utf-8") as handle:
        for line in open(src, encoding="utf-8"):
            text = line.rstrip("\n")
            for arm in ("N", "M"):
                work = os.path.join(scratch, "work", f"{label}-{arm}")
                text = text.replace(work + "/", "").replace(work, ".")
            text = text.replace(scratch, "<scratch>").replace(home, "<home>")
            text = re.sub(r"/tmp/claude-\d+[^\s\"'\\]*", "<tmp>", text)
            text = re.sub(r"/mnt/[\w./-]*" + re.escape(user), "<mnt>", text)
            text = re.sub(rf"\b{re.escape(user)}\b", "<user>", text)
            row = json.loads(text)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
