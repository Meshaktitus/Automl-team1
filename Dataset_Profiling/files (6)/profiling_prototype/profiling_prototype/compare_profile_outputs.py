"""Compares another team's profiling output with ours.
Usage:  python compare_profile_outputs.py our_output.json their_output.json
Prints: (1) problems when THEIR output is checked against OUR response schema, (2) field paths present in only one output,
(3) values that differ at paths both outputs share. Works with any JSON; array positions are shown as [] and column entries by name.
"""
import json
import sys
from pathlib import Path

from profiling_service import RESPONSE_SCHEMA
from schema_validation import validate


def paths(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(paths(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(node, list):
        for item in node:
            label = f"{prefix}[{item['name']}]" if isinstance(item, dict) and isinstance(item.get("name"), str) else f"{prefix}[]"
            out.update(paths(item, label))
        if not node:
            out[prefix + "[]"] = []
    else:
        out[prefix] = node
    return out


if len(sys.argv) != 3:
    sys.exit("Usage: python compare_profile_outputs.py our_output.json their_output.json")
ours, theirs = (json.loads(Path(a).read_text(encoding="utf-8")) for a in sys.argv[1:3])
a, b = paths(ours), paths(theirs)
generic = lambda s: __import__("re").sub(r"\[[^\]]+\]", "[]", s)     # drop column names to compare structure

print("== 1. Their output checked against our response schema ==")
problems = validate(theirs, RESPONSE_SCHEMA)
print("valid" if not problems else f"{len(problems)} problem(s):")
for path, msg in problems[:20]:
    print(f"  {path or '(root)'}: {msg}")

ga, gb = {generic(p) for p in a}, {generic(p) for p in b}
print("\n== 2. Field paths (structure) ==")
print("only in ours  :", ", ".join(sorted(ga - gb)[:25]) or "none")
print("only in theirs:", ", ".join(sorted(gb - ga)[:25]) or "none")

print("\n== 3. Different values at shared paths ==")
diff = [(p, a[p], b[p]) for p in sorted(set(a) & set(b)) if a[p] != b[p] and not p.endswith(("generated_at", "duration_ms", "request_id"))]
for p, x, y in diff[:25]:
    print(f"  {p}: ours {x!r} | theirs {y!r}")
print(f"{len(diff)} difference(s)" if diff else "none")
