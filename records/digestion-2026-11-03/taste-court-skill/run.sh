#!/usr/bin/env bash
# court-skill agent-level tasting (N, P, C), 2026-11-05.
#
#   T=<tasting dir> CLAUDE=<logged-in claude CLI> bash run.sh setup    # arm templates from $T/food (pinned clone)
#   T=... CLAUDE=... ORDER=N,P,C bash run.sh run                        # run the arms (resumable: same TASTE_OUT)
#   T=... CLAUDE=... bash run.sh grade                                  # blind grading + summary of every row
#
# Env: TASTE_OUT (default $T/out). The raw stream-json and the per-run work folders stay in $TASTE_OUT and are
# never published; rows/grades/summary are safe to commit.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
Q="$HERE/questions.json"
OUT="$(realpath -m "${TASTE_OUT:-$T/out}")"
MODEL=claude-opus-5-5
EFFORT=high
BUDGET=9000000   # court-skill's D13 cap is 10M; design and grading are digestion overhead
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
case "${1:-}" in
  setup)
    test "$(git -C "$T/food" rev-parse HEAD)" = 2abd32db25783720faf2589b456de944534f611d || { echo "food not at pin"; exit 2; }
    mkdir -p "$T/arms/N" "$T/arms/P" "$T/arms/C/.claude/skills"
    rm -rf "$T/arms/C/.claude/skills/court"
    cp -r "$T/food/skills/court" "$T/arms/C/.claude/skills/court"   # README's copy install, project scope
    printf '{"N": {"template": "%s"}, "P": {"template": "%s"}, "C": {"template": "%s"}}\n' \
      "$T/arms/N" "$T/arms/P" "$T/arms/C" > "$T/arms.json"
    find "$T/arms" -type f | sort
    ;;
  run)
    mkdir -p "$OUT"
    echo "out: $OUT"
    sha256sum "$Q"
    /usr/bin/python3 "$HERE/taste_run.py" --questions "$Q" --arms "$T/arms.json" --order "${ORDER:-N,P,C}" \
      --repeat 1 --claude "$CLAUDE" --out "$OUT" --budget "$BUDGET" --model "$MODEL" --effort "$EFFORT"
    echo "run exit $?"
    ;;
  grade)
    /usr/bin/python3 "$HERE/taste_grade.py" --questions "$Q" --rows "$OUT/rows.jsonl" --claude "$CLAUDE" \
      --out "$OUT/grades.jsonl" --model "$MODEL" --effort "$EFFORT"
    echo "grade exit $?"
    /usr/bin/python3 "$HERE/taste_summary.py" "$OUT/rows.jsonl" "$OUT/grades.jsonl" "$OUT/summary.json"
    ;;
  *) echo "usage: run.sh setup|run|grade"; exit 2 ;;
esac
