#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8000"

echo "Creating temp files..."
TMPDIR="$(mktemp -d)"
echo "hello world from student A" > "$TMPDIR/a.txt"
echo "hello world from student A" > "$TMPDIR/a_copy.txt"

echo "Submitting first work (student A)..."
RESP1="$(curl -s -F "student_id=studentA" -F "assignment_id=hw3" -F "file=@$TMPDIR/a.txt" "$BASE/works")"
echo "$RESP1" | python -c "import sys,json; print(json.loads(sys.stdin.read())['work']['id'])" > "$TMPDIR/wid1"
WID1="$(cat "$TMPDIR/wid1")"
echo "Work id: $WID1"

echo "Submitting second work (student B, same content -> plagiarism expected)..."
RESP2="$(curl -s -F "student_id=studentB" -F "assignment_id=hw3" -F "file=@$TMPDIR/a_copy.txt" "$BASE/works")"
echo "$RESP2" | python -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['report']['plagiarism'], d['report'].get('plagiarized_from_work_id'))"

echo "Fetching reports for second work..."
WID2="$(echo "$RESP2" | python -c "import sys,json; print(json.loads(sys.stdin.read())['work']['id'])")"
curl -s "$BASE/works/$WID2/reports" | python -m json.tool

echo "Smoke test done."
