"""The browser's row sets agree with `analysis.py`.

Compare decides Convergent and Fixed in the browser (`static/mutint_compare/compare_sets.js`),
and `analysis.py` is the reference those rules are written down in. Two implementations of one
rule drift unless something holds them together, so this runs the script under node over
random experiments and asserts the same ids, and the same reading of every threshold a
reader might type. It needs no database: `analysis` takes calls and samples, and these are
stand-ins with the four attributes it reads.

Skipped, saying why, where node is not installed.
"""

import random
import unittest
from types import SimpleNamespace

from mutint_common.util import get_gene_list

from mutint_compare import analysis
from mutint_compare.tests import browser_sets

#: Gene columns as the importer writes them: one gene, an intergenic pair, a range's bare
#: comma list, the no-gene marker, and nothing.
GENES = ["thrA", "thrB", "divB", "araJ", "thrA, thrB", "divB, araJ", "thrA,divB", "None", ""]
THRESHOLDS = ["1", "2", "3", "4", "50%", "33%", "33.4%", "100%", "0", "0%", "-1", "lots",
              "2.5", "101%", " 2 ", "+2", "1e1%", ".5%", "", "%", "50 %"]


def random_experiment(rng):
    populations = rng.randint(1, 4)
    samples = []
    for population in range(populations):
        for time in rng.sample([0, 100, 500, 1000, 1500, None], rng.randint(1, 4)):
            samples.append(SimpleNamespace(id=len(samples) + 1, population_id=population + 10,
                                           time_point=time))
    mutations = [SimpleNamespace(id=100 + i, gene=rng.choice(GENES)) for i in range(rng.randint(1, 12))]
    calls = [SimpleNamespace(sample_id=s.id, mutation_id=m.id, mutation=m, present=True)
             for s in samples for m in mutations if rng.random() < 0.35]
    return samples, mutations, calls


def as_state(samples, mutations, calls):
    """What the matrix hands the script: shown samples, and rows with a cell per sample."""
    index = {s.id: i for i, s in enumerate(samples)}
    rows = []
    for m in mutations:
        cells = [None] * len(samples)
        for call in calls:
            if call.mutation_id == m.id:
                cells[index[call.sample_id]] = {"f": "100%", "s": 1.0, "p": False}
        if any(cells):
            rows.append({"id": m.id, "genes": get_gene_list(m.gene), "cells": cells})
    return {"samples": [{"index": index[s.id], "population": str(s.population_id),
                         "time": s.time_point} for s in samples],
            "rows": rows}


@unittest.skipUnless(browser_sets.NODE, browser_sets.SKIP_REASON)
class SetsAgreeTestCase(unittest.TestCase):

    def test_random_experiments(self):
        rng = random.Random(20261001)
        jobs, expected = [], []
        for _ in range(300):
            samples, mutations, calls = random_experiment(rng)
            sample_dict = {s.id: s for s in samples}
            state = as_state(samples, mutations, calls)
            for name, fn in (("convergent", analysis.convergent_ids), ("fixed", analysis.fixed_ids)):
                text = rng.choice(["1", "2", "3", "50%", "67%", "100%"])
                jobs.append({"set": name, "state": state, "params": {name: text}})
                expected.append(sorted(fn(calls, sample_dict, at_least=analysis.Threshold.parse(text))))
        answers = browser_sets.run(jobs)
        for job, want, got in zip(jobs, expected, answers):
            self.assertEqual(want, got["ids"], job)

    def test_thresholds_read_the_same(self):
        answers = browser_sets.run([{"parse": text, "populations": 3} for text in THRESHOLDS])
        for text, got in zip(THRESHOLDS, answers):
            with self.subTest(text=text):
                try:
                    threshold = analysis.Threshold.parse(text)
                except ValueError:
                    self.assertTrue(got.get("error"), "the browser accepted %r" % text)
                    continue
                self.assertFalse(got.get("error"), "the browser refused %r" % text)
                self.assertEqual(threshold.count, got["count"])
                self.assertEqual(threshold.fraction, got["fraction"])
                self.assertEqual(threshold.needed(3), got["needed"])

    def test_the_defaults_are_the_same(self):
        answer = browser_sets.run([{"set": "convergent", "state": {"samples": [], "rows": []}},
                                   {"set": "fixed", "state": {"samples": [], "rows": []}}])
        defaults = analysis.Thresholds().as_dict()
        self.assertIn("(%s)" % defaults["convergent"], answer[0]["note"])
        self.assertIn("(%s)" % defaults["fixed"], answer[1]["note"])

    def test_a_threshold_that_reads_as_nothing_says_so_and_uses_the_default(self):
        state = {"samples": [], "rows": []}
        answer = browser_sets.run([{"set": "convergent", "state": state, "params": {"convergent": "lots"}}])
        self.assertIn("lots", answer[0]["error"])
        self.assertIn("using 2", answer[0]["error"])


class NoGeneTestCase(unittest.TestCase):
    """The importer writes the literal "None" into `Mutation.gene` for a mutation it could
    not annotate. It is no gene: counted as one, every unannotated mutation hit in two
    populations was "convergent" with every other."""

    def test_unannotated_mutations_do_not_converge_on_each_other(self):
        a = SimpleNamespace(id=1, population_id=1, time_point=1)
        b = SimpleNamespace(id=2, population_id=2, time_point=1)
        first = SimpleNamespace(id=10, gene="None")
        second = SimpleNamespace(id=11, gene="None")
        calls = [SimpleNamespace(sample_id=a.id, mutation_id=10, mutation=first, present=True),
                 SimpleNamespace(sample_id=b.id, mutation_id=11, mutation=second, present=True)]
        self.assertEqual(set(), analysis.convergent_ids(calls, {1: a, 2: b}))
