"""Neither set counts the ancestor's mutations.

An ancestral mutation is in every ALE by definition -- it was there before the first flask --
so left in, every one of them is convergent and, being in every flask, fixed in every
lineage. Both analyses would be measuring the starting line. Subtracting the ancestor
*sample* alone would look almost right: its column disappears while its mutations sit in
every other sample, which is exactly the state that produces the wrong answer. So the
assertions below are about the mutations.

The subtraction happens upstream, in `get_all_calls_filtered`; these prove it reaches the
sets, through the same inputs the view hands them.
"""

from django.test import TestCase

from mutint_compare.analysis import convergent_ids, fixed_ids
from mutint_experiment.models import Experiment, Population
from mutint_sample.models import Mutation, MutationCall, Sample
from mutint_sample.util import get_all_calls_filtered, get_ordered_sample_dict


class AncestorTestCase(TestCase):
    """Two ALEs of two flasks, plus an ancestor under ALE "0". `shared` is everywhere,
    `evolved` in both flasks of both ALEs."""

    def setUp(self):
        self.experiment = Experiment.objects.create()
        self.ancestor = self.make_sample("0", 1)
        evolved_samples = [self.make_sample(ale, flask) for ale in ("1", "2") for flask in (1, 2)]

        self.shared = self.make_mutation(100, "geneA")
        self.evolved = self.make_mutation(200, "geneB")
        for sample in [self.ancestor] + evolved_samples:
            self.observe(sample, self.shared)
        for sample in evolved_samples:
            self.observe(sample, self.evolved)

    def make_sample(self, ale_label, flask):
        ale, _ = Population.objects.get_or_create(experiment=self.experiment, name=ale_label)
        return Sample.objects.create(population=ale, time_point=flask, name="1", is_clonal=True)

    def make_mutation(self, position, gene):
        return Mutation.objects.create(experiment=self.experiment, mutation_type="SNP",
                                       start_position=position, seq_id="NC_000913",
                                       sequence_change="A>T", gene=gene)

    def observe(self, sample, mutation):
        return MutationCall.objects.create(sample=sample, mutation=mutation, present=True,
                                           source="breseq", frequency="1.0000")

    def sets(self):
        calls = get_all_calls_filtered(self.experiment.id)
        sample_dict = get_ordered_sample_dict(self.experiment.id)
        return convergent_ids(calls, sample_dict), fixed_ids(calls, sample_dict)


class TestWithoutADesignation(AncestorTestCase):
    def test_the_ancestral_mutation_looks_convergent_and_fixed(self):
        """The bug, stated as a test: with nothing designated it is in three ALEs and in
        every flask of each."""
        convergent, fixed = self.sets()
        self.assertIn(self.shared.id, convergent)
        self.assertIn(self.shared.id, fixed)


class TestWithADesignation(AncestorTestCase):
    def setUp(self):
        super().setUp()
        self.experiment.set_ancestor(self.ancestor)

    def test_the_ancestral_mutation_is_in_neither_set(self):
        convergent, fixed = self.sets()
        self.assertNotIn(self.shared.id, convergent)
        self.assertNotIn(self.shared.id, fixed)

    def test_a_genuinely_evolved_mutation_is_in_both(self):
        """The other half: an over-broad exclusion would empty the sets instead."""
        convergent, fixed = self.sets()
        self.assertIn(self.evolved.id, convergent)
        self.assertIn(self.evolved.id, fixed)
