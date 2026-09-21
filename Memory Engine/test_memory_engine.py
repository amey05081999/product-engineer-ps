# test_memory_engine.py
import unittest
from memory_engine import MemoryEngine, ACTIVE, SUPERSEDED, DELETED

FIXED_NOW = lambda: "2024-01-01T00:00:00+00:00"


class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine(now_fn=FIXED_NOW, deterministic_ids=True)

    # AC1: Store with provenance
    def test_store_with_provenance(self):
        m = self.engine.store(
            subject="user", predicate="lives_in", obj="Pune",
            source_message_id="msg-1", source_text="I live in Pune",
        )
        self.assertEqual(m.state, ACTIVE)
        info = self.engine.explain(m.id)
        self.assertEqual(info["source_message_id"], "msg-1")
        self.assertEqual(info["source_text"], "I live in Pune")

    # AC2: Relevant retrieval
    def test_bounded_relevant_retrieval(self):
        self.engine.store(subject="user", predicate="lives_in", obj="Pune",
                          source_message_id="m1", source_text="Pune")
        self.engine.store(subject="user", predicate="likes", obj="coffee",
                          source_message_id="m2", source_text="coffee")
        self.engine.store(subject="user", predicate="works_at", obj="Acme",
                          source_message_id="m3", source_text="Acme")
        results = self.engine.retrieve("where does the user live in pune", k=2)
        self.assertLessEqual(len(results), 2)
        self.assertTrue(any(r.memory.object == "Pune" for r in results))
        for r in results:
            self.assertGreater(r.evidence.score, 0)
            self.assertTrue(r.evidence.matched_fields)

    # AC3: Explicit correction and supersession
    def test_explicit_correction(self):
        old = self.engine.store(subject="user", predicate="lives_in", obj="Pune",
                                source_message_id="m1", source_text="Pune")
        new = self.engine.store(subject="user", predicate="lives_in", obj="Mumbai",
                                source_message_id="m2", source_text="Mumbai")
        self.assertEqual(self.engine.get(old.id).state, SUPERSEDED)
        self.assertEqual(self.engine.get(old.id).superseded_by, new.id)
        self.assertEqual(new.supersedes, old.id)
        results = self.engine.retrieve("where does the user live", k=5)
        objs = [r.memory.object for r in results]
        self.assertIn("Mumbai", objs)
        self.assertNotIn("Pune", objs)  # superseded excluded

    # AC4: Uncertain contradiction — conservative policy
    def test_ambiguous_conflict(self):
        self.engine.store(subject="user", predicate="lives_in", obj="Pune",
                          source_message_id="m1", source_text="Pune")
        cand = self.engine.store(subject="user", predicate="lives_in", obj="Mumbai",
                                 source_message_id="m2", source_text="maybe Mumbai",
                                 explicit_replace=False, confidence="low")
        # Existing stays active; candidate flagged conflict
        actives = [m for m in self.engine.all_memories() if m.state == ACTIVE
                   and not m.conflict]
        self.assertEqual(len(actives), 1)
        self.assertEqual(actives[0].object, "Pune")
        self.assertTrue(cand.conflict)
        # Retrieval returns only the non-conflict current memory
        results = self.engine.retrieve("where does the user live", k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].memory.object, "Pune")

    # AC5: Deletion
    def test_deletion(self):
        m = self.engine.store(subject="user", predicate="likes", obj="coffee",
                              source_message_id="m1", source_text="coffee")
        self.engine.delete(m.id)
        self.assertEqual(self.engine.get(m.id).state, DELETED)
        results = self.engine.retrieve("does the user like coffee", k=5)
        self.assertFalse(any(r.memory.id == m.id for r in results))

    # AC6: Determinism
    def test_determinism(self):
        e1 = MemoryEngine(now_fn=FIXED_NOW, deterministic_ids=True)
        e2 = MemoryEngine(now_fn=FIXED_NOW, deterministic_ids=True)
        for e in (e1, e2):
            e.store(subject="user", predicate="lives_in", obj="Pune",
                    source_message_id="m1", source_text="Pune")
            e.store(subject="user", predicate="likes", obj="coffee",
                    source_message_id="m2", source_text="coffee")
        r1 = e1.retrieve("where does the user live", k=5)
        r2 = e2.retrieve("where does the user live", k=5)
        self.assertEqual([r.memory.id for r in r1], [r.memory.id for r in r2])
        self.assertEqual([r.evidence.score for r in r1],
                         [r.evidence.score for r in r2])

    # Superseded chain inspection
    def test_supersession_chain(self):
        a = self.engine.store(subject="user", predicate="lives_in", obj="Pune",
                              source_message_id="m1", source_text="Pune")
        b = self.engine.store(subject="user", predicate="lives_in", obj="Mumbai",
                              source_message_id="m2", source_text="Mumbai")
        c = self.engine.store(subject="user", predicate="lives_in", obj="Delhi",
                              source_message_id="m3", source_text="Delhi")
        self.assertEqual(self.engine.get(a.id).superseded_by, b.id)
        self.assertEqual(self.engine.get(b.id).superseded_by, c.id)
        self.assertEqual(c.supersedes, b.id)
        # Only Delhi current
        results = self.engine.retrieve("where does the user live", k=5)
        self.assertEqual([r.memory.object for r in results], ["Delhi"])


if __name__ == "__main__":
    unittest.main()