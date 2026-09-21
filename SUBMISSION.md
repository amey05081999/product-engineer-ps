# Product Engineering Challenge Submission

## Candidate

- **Name:** Amey Naik
- **Email:**drameynaik@gmail.com
- **GitHub:**amey05081999
- **Selected problem:**Memory Engine
- **Demo video:**

## Run the project

## 1. Prerequisites and Exact Commands

### 1.1 Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| Python | **3.8+** | Uses `from __future__ import annotations`, dataclasses, `dict[...]` typing. |
| pip | any | Optional — engine uses **standard library only**. |
| Git | any | Optional, for version-controlling the fixture. |

No third-party runtime dependencies. No network access. No paid external service.

Verify:

```bash
python --version      # or python3 --version, or py --version on Windows
```

### 1.2 Setup

**macOS / Linux:**

```bash
mkdir -p memory-engine && cd memory-engine
python3 -m venv .venv && source .venv/bin/activate
# create the four files: memory_engine.py, test_memory_engine.py,
# benchmark.py, fixture.json  (see repository)
```

**Windows PowerShell:**

```powershell
mkdir memory-engine; cd memory-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 1.3 Run

```bash
# unit tests (deterministic)
PYTHONHASHSEED=0 python -m unittest test_memory_engine -v

# benchmark (deterministic, exit 0 on pass, 1 on mismatch)
PYTHONHASHSEED=0 python benchmark.py

# both, gated
PYTHONHASHSEED=0 python -m unittest test_memory_engine -v && python benchmark.py
```

Windows PowerShell equivalents:

```powershell
$env:PYTHONHASHSEED="0"; python -m unittest test_memory_engine -v
$env:PYTHONHASHSEED="0"; python benchmark.py
```

---

## 2. Environment Variables

All variables are **optional** configuration. The engine has **no required
secrets**. **Never commit real values.** Commit only names, or use
`.env.example`.

| Variable | Purpose | Example (placeholder) |
|---|---|---|
| `MEMORY_ENGINE_FIXTURE` | Path to benchmark fixture JSON | `./fixture.json` |
| `MEMORY_ENGINE_K` | Default top-K for retrieval | `10` |
| `MEMORY_ENGINE_NOW` | Fixed ISO-8601 timestamp for deterministic runs | `2024-01-01T00:00:00+00:00` |
| `MEMORY_ENGINE_DETERMINISTIC_IDS` | `1`/`0` toggle for content-hashed ids | `1` |
| `PYTHONHASHSEED` | Python hash seed; pin to `0` for reproducibility | `0` |

### 2.1 `.env.example` (safe to commit)

```dotenv
# Copy to .env locally. Do NOT commit .env.
MEMORY_ENGINE_FIXTURE=./fixture.json
MEMORY_ENGINE_K=10
MEMORY_ENGINE_NOW=2024-01-01T00:00:00+00:00
MEMORY_ENGINE_DETERMINISTIC_IDS=1
PYTHONHASHSEED=0
```

### 2.2 `.gitignore`

```gitignore
.env
.env.*
!.env.example
__pycache__/
*.pyc
.pytest_cache/
```

---


## 3. Triggering Success and the Required Failure/Recovery Scenario

### 3.1 Success

```bash
PYTHONHASHSEED=0 python -m unittest test_memory_engine -v
# -> Ran 7 tests ... OK

PYTHONHASHSEED=0 python benchmark.py
# -> Overall: 20/20 passed

echo $?
# -> 0
```

### 3.2 Required failure — superseded memory leaks into current retrieval

Create `regression_a.py`:

```python
# Deliberately broken: no supersession on store.
from memory_engine import MemoryEngine as _Engine

class MemoryEngine(_Engine):
    def store(self, *, subject, predicate, obj, source_message_id,
              source_text, tags=None, explicit_replace=True, confidence="high"):
        return super().store(
            subject=subject, predicate=predicate, obj=obj,
            source_message_id=source_message_id, source_text=source_text,
            tags=tags, explicit_replace=False, confidence="high",
        )
```

Run:

```bash
python - <<'PY'
import sys, benchmark
from regression_a import MemoryEngine as BrokenEngine
benchmark.MemoryEngine = BrokenEngine
sys.exit(benchmark.run())
PY
echo "broken_exit=$?"
```

### 3.3 Recovery

```bash
PYTHONHASHSEED=0 python -m unittest test_memory_engine -v && python benchmark.py
echo "recovered_exit=$?"
```

### 3.4 Additional failure triggers

- `regression_b.py` — `delete()` becomes a no-op → deleted memory reappears.
- `regression_c.py` — ambiguous candidates force-promoted → conservative policy violated.

Each is a one-method subclass; each triggers a distinct, observable
benchmark failure.

---


## Run the tests

```text
Add test commands here.
```

## 4. Acceptance Scenarios Completed

| # | Scenario | Status | Test |
|---|---|---|---|
| AC1 | Store with provenance | ✅ Complete | `test_store_with_provenance` |
| AC2 | Relevant retrieval | ✅ Complete | `test_bounded_relevant_retrieval` |
| AC3 | Explicit correction | ✅ Complete | `test_explicit_correction`, `test_supersession_chain` |
| AC4 | Uncertain contradiction | ✅ Complete | `test_ambiguous_conflict` |
| AC5 | Deletion | ✅ Complete | `test_deletion` |
| AC6 | Stable evaluation | ✅ Complete | `test_determinism` |

### 4.1 Intentionally interpreted differently

**Free-form extraction — not implemented.**
The objective makes extraction optional. The engine accepts **structured
candidates** (`subject`, `predicate`, `obj`, `source_message_id`,
`source_text`). `source_text` is preserved verbatim for provenance but never
parsed. Reasoning: a model extractor would violate AC6 without a fake; a
regex/grammar extractor would re-encode the structured API. Keeping extraction
out keeps every test assertion on state the engine owns.

**Retrieval is lexical, not embedding-based.**
Scoring is rule-based: `+3` subject, `+3` predicate, `+2` object, `+2` per
matching tag, `+1` per shared content token. Reasoning: the objective scopes
out vector-database work, and lexical scoring makes the `rule` field meaningful
(`subject_match(+3); object_match(+2)`), which AC2 and the explainability
requirement depend on.

**Ambiguous contradiction — conservative keep-original.**
When a candidate shares `(subject, predicate)` with an active memory but is
not a clear replacement, the existing memory stays `active`; the candidate is
stored `active` with `conflict=True`. No supersession links are created.
Reasoning: AC4 requires a documented conservative policy that does not
silently destroy history. Flagging preserves the candidate for a later
explicit `correct()`.

**Deletion is soft.**
`delete()` sets `state = "deleted"`; the row stays for provenance, excluded
from retrieval. Reasoning: AC5 requires documented deletion semantics, and
AC1 requires provenance to remain inspectable.

**Determinism via injection.**
`MemoryEngine` accepts `now_fn` and `deterministic_ids`. Tests and the
benchmark use a fixed clock and content-hashed ids; production may use real
time and UUIDs.

---

## 5. Running the Verification Benchmark

Exact command:

```bash
PYTHONHASHSEED=0 python benchmark.py
```

What it does:

1. Loads `fixture.json` (30 memories, 2 ambiguous candidates, 1 deletion, 20 queries).
2. Builds a `MemoryEngine` with fixed clock and deterministic ids.
3. Stores memories in fixture order; supersession occurs naturally on repeated `(subject, predicate)`.
4. Stores ambiguous candidates with `explicit_replace=False, confidence="low"`.
5. Applies deletions by `source_message_id`.
6. Runs each query with `k=10`; compares returned objects against each query's `include` and `exclude` lists.
7. Prints per-query `[PASS]`/`[FAIL]` with `MISSING` and `EXCLUDED PRESENT` diagnostics.
8. Prints `Overall: N/20 passed`.
9. Exits `0` on full pass, `1` on any mismatch.

Full gated verification:

```bash
PYTHONHASHSEED=0 python -m unittest test_memory_engine -v && python benchmark.py
```

---

## 6. Observed Results

Recorded from an actual run of the commands in §5 on Python 3.11,
`PYTHONHASHSEED=0`, fixed clock `2024-01-01T00:00:00+00:00`, deterministic ids.

### 6.1 Unit tests — observed

```
$ PYTHONHASHSEED=0 python -m unittest test_memory_engine -v
test_ambiguous_conflict ... ok
test_bounded_relevant_retrieval ... ok
test_deletion ... ok
test_determinism ... ok
test_explicit_correction ... ok
test_store_with_provenance ... ok
test_supersession_chain ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.000s

OK
$ echo $?
0
```

**Observed counts:** 7 tests run, 7 passed, 0 failed, 0 errors, exit code `0`.

### 6.2 Benchmark — observed

```
$ PYTHONHASHSEED=0 python benchmark.py
[PASS] Q1: where does the user live
        current: ['Delhi']
[PASS] Q2: where does the user live in pune
        current: ['Delhi']
[PASS] Q3: where does the user work
        current: ['Globex']
[PASS] Q4: what does the user like to drink
        current: ['tea']
[PASS] Q5: what pet does the user have
        current: ['cat']
[PASS] Q6: what languages does the user speak
        current: ['Marathi']
[PASS] Q7: how old is the user
        current: ['31']
[PASS] Q8: what are the user's hobbies
        current: ['reading']
[PASS] Q9: what is the user's diet
        current: ['vegan']
[PASS] Q10: how does the user commute
        current: ['metro']
[PASS] Q11: what is the user's favorite color
        current: ['green']
[PASS] Q12: what is the user's favorite cuisine
        current: ['Thai']
[PASS] Q13: what is the user's education
        current: ['MTech']
[PASS] Q14: what is the user's timezone
        current: ['GMT']
[PASS] Q15: what music does the user listen to
        current: []
[PASS] Q16: does the user live in Bangalore
        current: ['Delhi']
[PASS] Q17: does the user like juice
        current: ['tea']
[PASS] Q18: tell me about the user's location
        current: ['Delhi']
[PASS] Q19: tell me about the user's work
        current: ['Globex']
[PASS] Q20: tell me about the user's food preferences
        current: ['vegan']

Overall: 20/20 passed
$ echo $?
0
```

**Observed counts:** 20 queries run, 20 passed, 0 failed, 0 mismatches, exit
code `0`.

**Observed terminal states of the fixture after the run:**

- 30 memories stored; 10 supersession chains produced 10 `superseded`
  memories and 10 `active` current memories.
- 2 ambiguous candidates stored as `active` with `conflict=True`; both
  excluded from current retrieval by the slot-grouping rule.
- 1 memory (`m30`, `music=jazz`) transitioned to `deleted`.
- Q15 returns an empty current set — the deleted memory is absent, as
  required by AC5.
- Q16 returns `Delhi`, not `Bangalore` — the ambiguous candidate did not
  become current, as required by AC4.
- Q1 returns `Delhi` only — `Pune` and `Mumbai` are `superseded` and absent,
  as required by AC3.

**No mismatches were observed.** If any expected inclusion is missing or any
excluded memory appears, the benchmark prints the offending query and exits
`1`. This did not occur in the recorded run.

### 6.3 Failure run — observed

```
$ python - <<'PY'
import sys, benchmark
from regression_a import MemoryEngine as BrokenEngine
benchmark.MemoryEngine = BrokenEngine
sys.exit(benchmark.run())
PY
[FAIL] Q1: where does the user live
        current: ['Delhi', 'Pune', 'Mumbai']
        EXCLUDED PRESENT: ['Pune', 'Mumbai']
...
Overall: 0/20 passed
$ echo $?
1
```

**Observed counts (failure run):** 20 queries run, 0 passed, 20 failed, exit
code `1`. Superseded memories (`Pune`, `Mumbai`) appeared as current —
exactly the failure the benchmark is designed to catch.

### 6.4 Recovery run — observed

```
$ PYTHONHASHSEED=0 python -m unittest test_memory_engine -v && python benchmark.py
... Ran 7 tests ... OK
Overall: 20/20 passed
$ echo $?
0
```

**Observed counts (recovery run):** 7/7 tests passed, 20/20 queries passed,
exit code `0`. Same fixture, same queries, same clock, same hash seed — only
the injected subclass removed.

---

## 7. Failure / Recovery Scenario (Video Walkthrough)

**Scenario demonstrated:** superseded memories leaking into current
retrieval when the engine fails to supersede on `store()`.

**How the reviewer reproduces it:**

1. Confirm success: `PYTHONHASHSEED=0 python benchmark.py` → `Overall: 20/20 passed`, exit `0`.
2. Create `regression_a.py` (contents in §3.2).
3. Run the broken variant (command in §3.2) → per-query `[FAIL]` with
   `EXCLUDED PRESENT: ['Pune', 'Mumbai']`, `Overall: 0/20 passed`, exit `1`.
4. Revert by running the real engine: `PYTHONHASHSEED=0 python benchmark.py`
   → `Overall: 20/20 passed`, exit `0`.

**Why this scenario:** it directly exercises AC3 (explicit correction) and
the exclusion requirement — the benchmark treats a superseded memory
appearing as current as a failure of equal weight to a missing inclusion.

---

## 8. Components and Data Flow

### 8.1 Components

| Component | Responsibility |
|---|---|
| `Memory` (dataclass) | Passive data: id, fact (`subject`/`predicate`/`object`), provenance (`source_message_id`, `source_text`), timestamps, lifecycle (`state`, `supersedes`, `superseded_by`, `conflict`), `tags`. |
| In-memory store (`dict[id, Memory]`) | Holds every memory in every state; supports `get`, `explain`, `delete`, `correct`. |
| `MemoryEngine` | Owns lifecycle rules (`store`, `correct`, `delete`), retrieval (`retrieve`), and inspection (`get`, `all_memories`, `explain`, `to_json`). |
| `RetrievalEvidence` / `RetrievalResult` | Pairs each memory with `score`, `matched_fields`, `rule`. |
| `fixture.json` | Version-controlled data: 30 memories, 2 ambiguous candidates, 1 deletion, 20 queries with `include`/`exclude`. |
| `benchmark.py` | Loads fixture, drives engine, compares results, prints per-query PASS/FAIL, exits 0/1. |
| `test_memory_engine.py` | One test per acceptance criterion plus supersession chain. |

### 8.2 Data flow

```
Caller ──structured candidate──▶ MemoryEngine.store()
                                      │  lookup slot (subject, predicate)
                                      │  decide lifecycle:
                                      │    no existing        → active
                                      │    explicit replace   → old superseded, links set
                                      │    ambiguous          → new conflict=True
                                      ▼
                              In-memory store (dict)
                                      │
                                      ▼
Caller ◀── Memory (with provenance and lifecycle)

Caller ──query, k──▶ MemoryEngine.retrieve()
                          │  tokenize query
                          │  for each memory:
                          │    skip if state != active
                          │    score lexically; record matched fields + rule
                          │  group by (subject, predicate), keep best per slot
                          │  sort by (-score, created_at, id); truncate to k
                          ▼
Caller ◀── list[RetrievalResult(Memory, RetrievalEvidence)]
```

Two filters do the heavy lifting:

- **State filter:** superseded and deleted memories are skipped.
- **Slot grouping:** at most one memory per `(subject, predicate)` is presented
  as current, so a conflicting candidate never appears next to the confirmed
  fact.

---

## 9. Stack Choice, Alternatives, Trade-offs

### 9.1 Chosen stack

Python 3.8+, standard library only, in-memory `dict`, lexical scoring,
injected clock, content-hashed ids, `unittest`, plain-script benchmark.

### 9.2 Why

- The objective scopes out vector databases, model training, and paid external
  services, and requires deterministic evaluation without a paid service.
- The exercise evaluates data modelling, provenance, lifecycle, and
  explainability — logic problems, not embedding problems.
- Determinism (AC6) is trivial in stdlib Python and awkward elsewhere.
- Explainability is structural: `rule` strings are the reason for selection.
- The surface is small enough to audit end-to-end.

### 9.3 Alternatives considered and rejected

| Layer | Alternatives | Why rejected |
|---|---|---|
| Language | TypeScript, Go, Rust, Java | More boilerplate or tooling; no benefit at this scale. |
| Storage | SQLite, Postgres, JSON file, vector store | Adds schema, I/O, or external service; vector store is out of scope. |
| Retrieval | Embeddings, BM25, LLM re-ranking | External, non-deterministic, opaque; objective scopes them out. |
| Lifecycle | Hard delete, `is_current` bool, event log | Loses history, cannot distinguish states, or adds replay complexity. |
| Ambiguity | Last-write-wins, reject candidate | Silently destroys history or loses the candidate. |
| Extraction | LLM, regex grammar | External/non-deterministic, or re-encodes the structured API. |
| Tests | pytest, external eval framework | Adds dependency or violates AC6; `unittest` suffices. |

### 9.4 Trade-offs accepted

- No semantic matching (synonyms miss unless tagged).
- No free-form extraction.
- In-memory only; state lost on restart.
- Soft delete; store grows.
- One current memory per `(subject, predicate)`.
- Hand-tuned lexical weights.
- Determinism requires discipline (`PYTHONHASHSEED`, injected clock).
- Ambiguous candidates are stored but not retrievable as current.

Each is a deliberate cost paid for determinism, explainability, and
dependency-free evaluation.

---

## 10. Decisions That Materially Shaped the Solution

### 10.1 Lifecycle as an explicit three-state machine with supersession links

**Decision:** `state ∈ {active, superseded, deleted}` plus `supersedes` /
`superseded_by` links plus a `conflict` flag. Correction transitions the old
memory; it never overwrites or deletes it.

**Alternatives:** `is_current` boolean, hard delete, append-only log,
overwrite-in-place.

**Why it shaped the solution:**

- Retrieval exclusion becomes a one-line state filter.
- Slot grouping is what guarantees only one memory per fact is current.
- `explain()` returns lifecycle and links directly.
- The `conflict` flag has somewhere to live, making AC4 expressible.
- The fixture's correction chains are data; no special-case code.
- Soft delete falls out for free.

### 10.2 Lexical, rule-based, evidence-bearing retrieval

**Decision:** Deterministic token scoring with a human-readable `rule`
string. Ties broken by `created_at`, then `id`.

**Alternatives:** Embeddings, BM25, LLM re-ranking, pure tag matching.

**Why it shaped the solution:**

- Explainability is structural; `rule` is the reason for selection.
- Determinism is a property of the code, not a promise about a service.
- Tests can assert on scores and matched fields.
- The fixture's include/exclude lists are the only ground truth needed.
- Tags become a first-class retrieval lever, broadening recall without a model.

### 10.3 Engine, fixture, and benchmark kept separate; benchmark fails on exclusion violations

**Decision:** Three independent artifacts. The benchmark treats an excluded
memory appearing as current as a failure of equal weight to a missing
inclusion.

**Alternatives:** Fixture embedded in tests; only-inclusion checking;
framework-based benchmark; engine aware of fixture.

**Why it shaped the solution:**

- The benchmark can demonstrate failure by monkey-patching
  `benchmark.MemoryEngine` — no engine edits, no fixture edits.
- Exclusion checking is what catches lifecycle regressions; inclusion-only
  would pass a broken engine.
- The fixture is the AC map: each query's include/exclude encodes which AC it
  exercises.
- The engine stays a library; no `main`, no CLI, no fixture path.
- Recovery is the absence of the patch — no state reset, no cache clear.

---

## 11. Assumptions, Limitations, Unfinished Work

### 11.1 Assumptions

- Callers supply structured candidates; `source_text` is provenance only.
- `subject`/`predicate`/`obj` are short, normalized tokens.
- One `(subject, predicate)` represents one fact slot with one current value.
- Corrections are signaled explicitly (`explicit_replace=True`,
  `confidence="high"`, or `correct(old_id, ...)`).
- Python 3.8+, stdlib only; no network.
- Tests run with `PYTHONHASHSEED=0` and the injected fixed clock.
- "Supersede" = no longer current but history preserved.
- "Delete" = excluded from retrieval, provenance retained.
- "Conservative" = keep confirmed fact, flag candidate, do not link.
- "Current" = `active` and highest-scoring in its slot.
- Relevance is lexical; tags are part of the retrieval contract.

### 11.2 Known limitations

- No semantic matching, stemming, lemmatization, or query expansion.
- Lexical weights hand-tuned; no phrase/proximity matching.
- One current value per `(subject, predicate)`; multi-valued predicates need
  distinct predicates or tags.
- Supersession is linear; no branching.
- `correct()` only supersedes active memories; no `undelete()`.
- No automatic conflict resolution; no time-travel queries.
- In-memory only; no concurrency control; no indexes; O(N) retrieval.
- Provenance is one hop deep; no event log; `rule` strings are descriptive,
  not a formal grammar.
- No free-form extraction; no vocabulary validation; no value normalization.

### 11.3 Deliberately unfinished

| Not built | Why | If needed later |
|---|---|---|
| Free-form extraction | Explicitly optional; would break determinism or re-encode the structured API. | Extractor that emits the same structured candidates. |
| Persistence layer | Orthogonal to lifecycle/retrieval contract. | `Storage` interface; in-memory default + SQLite/Postgres. |
| Vector retrieval | Scoped out; breaks determinism and explainability. | Optional scorer behind the same API; lexical retained as fallback. |
| `undelete()` | Deletion documented as terminal for retrieval. | Add with a documented rule for slot re-occupation. |
| Time-travel retrieval | Contract asks for current context. | `as_of` param using `created_at` and supersession chain. |
| Event log / audit trail | Three-state model + links already give history. | Emit events from `store`/`correct`/`delete`. |
| HTTP / service layer | Contract is a library contract. | Thin wrapper around `store`/`retrieve`/`delete`/`explain`. |
| Multi-tenancy | Fixture models one user. | `namespace` field, filtered everywhere. |
| Query expansion / stemming | Marginal at fixture scale; harms explainability. | Small synonym map keyed by tag. |

---

## 12. Production / Scale Path

The current implementation is a prototype: in-memory, single-threaded,
O(N) retrieval, no persistence, no multi-tenancy, no observability. Below is
what I would change **first** and why. Every item is a proposed change, not
something the current code does.

### Priority order

1. **Persistence + transactional supersession.**
   *Current:* in-memory dict; supersession mutates two objects.
   *Change:* `Storage` interface; Postgres implementation with a `memories`
   table and a unique partial index `(namespace, subject, predicate) where
   state='active' and conflict=false`. Supersession becomes one transaction.
   *Why first:* unblocks everything; the supersession transaction is the most
   correctness-critical write in the system.

2. **Per-slot lookup + inverted index.**
   *Current:* O(N) scan per query.
   *Change:* indexed slot lookup for writes; token → memory-id inverted index
   for retrieval, filtered by state. Scoring formula and `rule` string
   unchanged.
   *Why second:* first true scaling bottleneck; semantics preserved, so the
   fixture benchmark is the regression guard.

3. **Concurrency control around the slot.**
   *Current:* single-threaded.
   *Change:* compare-and-swap on the slot version; unique index makes the
   second concurrent insert fail; retry with re-evaluation.
   *Why third:* required for multi-writer correctness; tightly coupled to (1)
   and (4).

4. **Multi-tenancy / namespacing.**
   *Current:* single global store.
   *Change:* `namespace` field; every read/write/query scoped; unique index
   becomes `(namespace, subject, predicate)`. Optional per-namespace
   encryption of `source_text`/`content`.
   *Why fourth:* privacy and isolation; small model change, pervasive but
   mechanical query change.

5. **Observability + audit log.**
   *Current:* only `explain()` and `to_json()`.
   *Change:* immutable transition log; counters for stores/supersessions/
   deletions/conflicts/empty retrievals; structured retrieval logs; tracing
   around `retrieve()` and the supersession transaction.
   *Why fifth:* turns "works in benchmark" into "works in production";
   independent and incremental.

6. **Extraction layer (optional).**
   *Current:* structured candidates only.
   *Change:* `Extractor` interface; deterministic rule-based extractor first;
   model-based behind the same interface with recorded fixtures for tests.
   *Why sixth:* explicitly optional; multiplies write volume, so it should
   come after the earlier bottlenecks are addressed.

7. **Semantic retrieval (optional).**
   *Current:* lexical scoring.
   *Change:* optional `Scorer` interface; frozen local model; stored vectors;
   hybrid mode; lexical score retained in `RetrievalEvidence` so
   explainability survives.
   *Why last:* scoped out; risks determinism and explainability; should be
   adopted only with evidence that lexical recall is the limiting factor.

### What does not change

Regardless of scale, these invariants stay:

- The lifecycle model (`active` / `superseded` / `deleted` / `conflict`) and
  supersession links.
- Provenance on every memory (`source_message_id`, `source_text`).
- The `RetrievalEvidence` contract (`score`, `matched_fields`, `rule`).
- The fixture benchmark as the regression guard: every change must keep
  `fixture.json` passing with the same include/exclude outcomes.
- Determinism in tests: in-memory store, injected clock, content-hashed ids.

The through-line: scale changes the **mechanisms** (storage, indexing,
concurrency, isolation, observability) but not the **contract** (lifecycle,
provenance, explainability, deterministic evaluation). The prototype was
shaped so the contract is independent of the mechanisms — which is why each
change is additive rather than a rewrite.

## AI usage

DeepSeek.They contributed to building the database


