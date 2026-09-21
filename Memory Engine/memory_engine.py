# memory_engine.py
"""
Small memory engine: store, retrieve, correct, delete, explain.
Standard library only. Deterministic by default.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

ACTIVE = "active"
SUPERSEDED = "superseded"
DELETED = "deleted"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


@dataclass
class Memory:
    id: str
    subject: str
    predicate: str
    object: str
    content: str
    source_message_id: str
    source_text: str
    created_at: str
    updated_at: str
    state: str = ACTIVE
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    conflict: bool = False  # ambiguous contradiction flag

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RetrievalEvidence:
    memory_id: str
    score: float
    matched_fields: list[str]
    rule: str


@dataclass
class RetrievalResult:
    memory: Memory
    evidence: RetrievalEvidence


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MemoryEngine:
    def __init__(self, now_fn: Optional[Callable[[], str]] = None,
                 deterministic_ids: bool = True):
        self._memories: dict[str, Memory] = {}
        self._now_fn = now_fn or (lambda: "2024-01-01T00:00:00+00:00")
        self._deterministic_ids = deterministic_ids

    # -- helpers ------------------------------------------------------------

    def _now(self) -> str:
        return self._now_fn()

    def _make_id(self, subject: str, predicate: str, obj: str,
                 source_message_id: str) -> str:
        if self._deterministic_ids:
            raw = f"{subject}|{predicate}|{obj}|{source_message_id}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        import uuid
        return uuid.uuid4().hex

    # -- storage ------------------------------------------------------------

    def store(self, *, subject: str, predicate: str, obj: str,
              source_message_id: str, source_text: str,
              tags: Optional[list[str]] = None,
              explicit_replace: bool = True,
              confidence: str = "high") -> Memory:
        """
        Store a structured memory candidate.

        explicit_replace=True  -> if an active memory with same (subject,predicate)
                                  exists, this new one supersedes it.
        explicit_replace=False -> ambiguous; conservative policy applies.
        """
        tags = tags or []
        now = self._now()
        mem_id = self._make_id(subject, predicate, obj, source_message_id)
        content = f"{subject} {predicate} {obj}"

        # Look for an existing active memory with same subject+predicate
        existing = self._find_active(subject, predicate)

        new_mem = Memory(
            id=mem_id,
            subject=subject,
            predicate=predicate,
            object=obj,
            content=content,
            source_message_id=source_message_id,
            source_text=source_text,
            created_at=now,
            updated_at=now,
            tags=list(tags),
        )

        if existing is not None and existing.object != obj:
            if explicit_replace and confidence == "high":
                # Explicit correction: supersede
                existing.state = SUPERSEDED
                existing.superseded_by = new_mem.id
                existing.updated_at = now
                new_mem.supersedes = existing.id
            else:
                # Ambiguous: conservative policy — keep existing current,
                # store candidate as active but flagged conflict.
                new_mem.conflict = True
                new_mem.tags = sorted(set(new_mem.tags) | {"conflict"})

        self._memories[new_mem.id] = new_mem
        return new_mem

    def _find_active(self, subject: str, predicate: str) -> Optional[Memory]:
        candidates = [
            m for m in self._memories.values()
            if m.state == ACTIVE and m.subject == subject
            and m.predicate == predicate and not m.conflict
        ]
        if not candidates:
            return None
        # Deterministic: earliest created wins as "current"
        return sorted(candidates, key=lambda m: (m.created_at, m.id))[0]

    # -- correction / deletion ---------------------------------------------

    def correct(self, old_id: str, *, subject: str, predicate: str, obj: str,
                source_message_id: str, source_text: str,
                tags: Optional[list[str]] = None) -> Memory:
        """Explicit correction targeting a specific memory id."""
        old = self._memories.get(old_id)
        if old is None:
            raise KeyError(f"unknown memory id: {old_id}")
        new_mem = self.store(
            subject=subject, predicate=predicate, obj=obj,
            source_message_id=source_message_id, source_text=source_text,
            tags=tags, explicit_replace=True, confidence="high",
        )
        if old.state == ACTIVE:
            old.state = SUPERSEDED
            old.superseded_by = new_mem.id
            old.updated_at = self._now()
            new_mem.supersedes = old.id
        return new_mem

    def delete(self, memory_id: str) -> Memory:
        m = self._memories.get(memory_id)
        if m is None:
            raise KeyError(f"unknown memory id: {memory_id}")
        m.state = DELETED
        m.updated_at = self._now()
        # If this memory superseded another, that one stays superseded.
        # If this memory was superseded, it stays deleted.
        return m

    # -- retrieval ----------------------------------------------------------

    def retrieve(self, query: str, k: int = 5) -> list[RetrievalResult]:
        q_tokens = _tokens(query)
        scored: list[tuple[float, Memory, list[str], str]] = []

        for m in self._memories.values():
            if m.state != ACTIVE:
                continue
            score = 0.0
            matched: list[str] = []
            rule_parts: list[str] = []

            if m.subject.lower() in q_tokens:
                score += 3
                matched.append("subject")
                rule_parts.append("subject_match(+3)")
            if m.predicate.lower() in q_tokens:
                score += 3
                matched.append("predicate")
                rule_parts.append("predicate_match(+3)")
            if m.object.lower() in q_tokens:
                score += 2
                matched.append("object")
                rule_parts.append("object_match(+2)")
            tag_hits = [t for t in m.tags if t.lower() in q_tokens]
            if tag_hits:
                score += 2 * len(tag_hits)
                matched.append("tags")
                rule_parts.append(f"tag_match(+{2*len(tag_hits)})")
            content_overlap = q_tokens & _tokens(m.content)
            if content_overlap:
                score += len(content_overlap)
                matched.append("content")
                rule_parts.append(f"content_overlap(+{len(content_overlap)})")

            if score > 0:
                rule = "; ".join(rule_parts) or "no_rule"
                scored.append((score, m, matched, rule))

        # Group by (subject, predicate) — keep best per group so superseded/
        # conflicting memories don't both appear as current.
        best_per_key: dict[tuple[str, str], tuple[float, Memory, list[str], str]] = {}
        for item in scored:
            key = (item[1].subject, item[1].predicate)
            if key not in best_per_key or item[0] > best_per_key[key][0]:
                best_per_key[key] = item

        ordered = sorted(
            best_per_key.values(),
            key=lambda x: (-x[0], x[1].created_at, x[1].id),
        )[:k]

        return [
            RetrievalResult(
                memory=m,
                evidence=RetrievalEvidence(
                    memory_id=m.id, score=s, matched_fields=mf, rule=r,
                ),
            )
            for s, m, mf, r in ordered
        ]

    # -- inspection ---------------------------------------------------------

    def get(self, memory_id: str) -> Memory:
        return self._memories[memory_id]

    def all_memories(self) -> list[Memory]:
        return sorted(self._memories.values(), key=lambda m: m.id)

    def explain(self, memory_id: str) -> dict:
        m = self._memories[memory_id]
        return {
            "id": m.id,
            "content": m.content,
            "state": m.state,
            "source_message_id": m.source_message_id,
            "source_text": m.source_text,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
            "supersedes": m.supersedes,
            "superseded_by": m.superseded_by,
            "conflict": m.conflict,
            "tags": m.tags,
        }

    def to_json(self) -> str:
        return json.dumps([m.to_dict() for m in self.all_memories()],
                          indent=2, sort_keys=True)