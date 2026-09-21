# benchmark.py
"""
Repeatable benchmark: loads fixture, builds engine, runs queries,
compares against expected inclusions/exclusions, reports per-query
results and overall pass count. Fails (exit 1) if any mismatch.
"""
import json
import sys
from memory_engine import MemoryEngine

FIXED_NOW = lambda: "2024-01-01T00:00:00+00:00"


def run(fixture_path: str = "fixture.json") -> int:
    with open(fixture_path) as f:
        fixture = json.load(f)

    engine = MemoryEngine(now_fn=FIXED_NOW, deterministic_ids=True)

    # Store memories in order (corrections happen naturally via same subject/predicate)
    for m in fixture["memories"]:
        engine.store(
            subject=m["subject"], predicate=m["predicate"], obj=m["obj"],
            source_message_id=m["source_message_id"],
            source_text=m["source_text"], tags=m.get("tags", []),
        )

    # Ambiguous candidates
    for a in fixture.get("ambiguous", []):
        engine.store(
            subject=a["subject"], predicate=a["predicate"], obj=a["obj"],
            source_message_id=a["source_message_id"],
            source_text=a["source_text"], tags=a.get("tags", []),
            explicit_replace=a.get("explicit_replace", False),
            confidence=a.get("confidence", "low"),
        )

    # Deletions by source_message_id
    for mid in fixture.get("deletions", []):
        for mem in engine.all_memories():
            if mem.source_message_id == mid:
                engine.delete(mem.id)

    passed = 0
    total = len(fixture["queries"])
    failures = []

    for i, q in enumerate(fixture["queries"], 1):
        results = engine.retrieve(q["q"], k=10)
        current = [r.memory.object for r in results]
        current_lower = [c.lower() for c in current]

        missing = [inc for inc in q["include"]
                   if inc.lower() not in current_lower]
        present_excluded = [exc for exc in q["exclude"]
                            if exc.lower() in current_lower]

        ok = not missing and not present_excluded
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failures.append((i, q["q"], missing, present_excluded, current))

        print(f"[{status}] Q{i}: {q['q']}")
        print(f"        current: {current}")
        if missing:
            print(f"        MISSING: {missing}")
        if present_excluded:
            print(f"        EXCLUDED PRESENT: {present_excluded}")

    print(f"\nOverall: {passed}/{total} passed")
    if failures:
        print("Failures:")
        for f in failures:
            print(f"  Q{f[0]}: {f[1]} | missing={f[2]} | excluded_present={f[3]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())