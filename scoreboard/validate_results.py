#!/usr/bin/env python3
"""Validate every row of scoreboard/results.jsonl against schema/result.schema.json, plus
consistency checks the schema cannot express (unique run ids, totals add up, tree links valid).
Exit code 1 on any failure. Needs: pip install jsonschema"""
import json, os, sys
from jsonschema import Draft202012Validator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
schema = json.load(open(os.path.join(ROOT, "schema", "result.schema.json")))
course = json.load(open(os.path.join(ROOT, "course.json")))
node_ids = {n["id"] for n in course["nodes"]}
V = Draft202012Validator(schema)
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scoreboard", "results.jsonl")
errors, seen, n = [], set(), 0
for i, line in enumerate(open(path), 1):
    if not line.strip():
        continue
    n += 1
    row = json.loads(line)
    for e in V.iter_errors(row):
        errors.append(f"line {i}: {'/'.join(map(str, e.path))}: {e.message}")
    rid = row.get("run_id")
    if rid in seen:
        errors.append(f"line {i}: duplicate run_id {rid}")
    seen.add(rid)
    try:
        raw = round(sum(row["node_splits"].values()), 2)
        tot = round(raw + sum(p["s"] for p in row["penalties"]) - sum(b["s"] for b in row["bonuses"]), 2)
        if abs(raw - row["raw_time_s"]) > 0.05 or abs(tot - row["total_time_s"]) > 0.05:
            errors.append(f"line {i}: totals do not add up ({raw}/{tot} vs {row['raw_time_s']}/{row['total_time_s']})")
        ids = {t["node_id"] for t in row["node_tree"]}
        for t in row["node_tree"]:
            if t["node_id"] not in node_ids:
                errors.append(f"line {i}: unknown node {t['node_id']}")
            if t["parent_node_id"] is not None and t["parent_node_id"] not in ids:
                errors.append(f"line {i}: node {t['node_id']} parent {t['parent_node_id']} not in tree")
    except KeyError as e:
        errors.append(f"line {i}: missing {e}")
print(f"{n} rows checked, {len(errors)} problems")
for e in errors[:50]:
    print("  ", e)
sys.exit(1 if errors else 0)
