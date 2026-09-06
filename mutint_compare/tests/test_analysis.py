"""The two rules and their thresholds, over calls built by hand.

Ported from mutint-converge's and mutint-fixation's rule tests when those plugins became
Compare's Show menu. The rules are unchanged at their defaults; what is new is the threshold.
Runs only in an assembled project: `./mutint test mutint_compare`.
"""

from django.test import RequestFactory, TestCase

from mutint_compare import analysis
from mutint_compare.analysis import Threshold, Thresholds, convergent_ids, fixed_ids
from mutint_experiment.models import Experiment, Population
from mutint_filter.view_filter import ViewFilter
from mutint_sample.models import Mutation, MutationCall, Sample
from mutint_sample.util import get_all_calls_filtered, get_reseq_ordered_dict


class ThresholdTestCase(TestCase):
    def test_a_number_is_that_many_populations(self):
        self.assertEqual(3, Threshold.parse("3").needed(10))
        self.assertEqual("3", str(Threshold.parse(" 3 ")))

    def test_a_percentage_is_a_fraction_rounded_up(self):
        half = Threshold.parse("50%")
        self.assertEqual(2, half.needed(3), "half of three is two, not one")
        self.assertEqual(2, half.needed(4))
        self.assertEqual(1, Threshold.parse("33.3%").needed(3), "a third of three is one")
        self.assertEqual("50%", str(half))

    def test_a_fraction_asks_for_at_least_one(self):
        self.assertEqual(1, Threshold.parse("10%").needed(0))
        self.assertEqual(1, Threshold.parse("10%").needed(1))

    def test_nothing_and_nonsense_are_refused(self):
        for text in ("", "0", "-1", "0%", "101%", "two", "%"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    Threshold.parse(text)

    def test_the_defaults_are_the_old_rules(self):
        thresholds = Thresholds()
        self.assertEqual(2, thresholds.convergent.needed(50), "more than one ALE")
        self.assertEqual(1, thresholds.fixed.needed(50), "any ALE")


class ThresholdRequestTestCase(TestCase):
    """Read when present, remembered in the session, defaulted when nonsense."""

    def _request(self, **params):
        request = RequestFactory().get("/compare/", params)
        request.session = {}
        return request

    def test_present_parameters_are_read_and_remembered(self):
        request = self._request(convergent_min="3", fixed_min="50%")
        thresholds = analysis.get_thresholds(request, 7)
        self.assertEqual("3", str(thresholds.convergent))
        self.assertEqual("50%", str(thresholds.fixed))
        self.assertEqual({"7": {"convergent": "3", "fixed": "50%"}},
                         request.session[analysis.SESSION_KEY])

    def test_absent_parameters_fall_back_to_the_session_then_the_defaults(self):
        request = self._request()
        request.session[analysis.SESSION_KEY] = {"7": {"convergent": "4", "fixed": "2"}}
        self.assertEqual("4", str(analysis.get_thresholds(request, 7).convergent))
        self.assertEqual(Thresholds(), analysis.get_thresholds(request, 8))

    def test_nonsense_reverts_that_threshold_to_its_default(self):
        request = self._request(convergent_min="lots", fixed_min="2")
        thresholds = analysis.get_thresholds(request, 7)
        self.assertEqual(analysis.DEFAULT_CONVERGENT, thresholds.convergent)
        self.assertEqual("2", str(thresholds.fixed))


class _Rules(TestCase):
    """One experiment, samples by (ALE, time point), calls by hand."""

    def setUp(self):
        self.experiment = Experiment.objects.create()
        self.ales = {}

    def sample(self, ale, time_point=1, name="1"):
        population = self.ales.get(ale)
        if population is None:
            population = self.ales[ale] = Population.objects.create(
                name=ale, experiment=self.experiment)
        return Sample.objects.create(population=population, time_point=time_point,
                                     name=name, is_clonal=True)

    def mutation(self, position, gene="thrA"):
        return Mutation.objects.create(
            experiment=self.experiment, mutation_type="SNP", start_position=position,
            sequence_change="A>T", gene=gene)

    def observe(self, sample, mutation):
        return MutationCall.objects.create(sample=sample, mutation=mutation,
                                           present=True, frequency=1)

    def inputs(self, view_filter=None):
        """What the view hands the analysis: the page's samples and its filtered calls."""
        return (get_all_calls_filtered(self.experiment.id, view_filter=view_filter),
                get_reseq_ordered_dict(self.experiment.id))

    def convergent(self, at_least="2", view_filter=None):
        calls, reseq_dict = self.inputs(view_filter)
        return convergent_ids(calls, reseq_dict, at_least=Threshold.parse(at_least))

    def fixed(self, at_least="1", view_filter=None):
        calls, reseq_dict = self.inputs(view_filter)
        return fixed_ids(calls, reseq_dict, at_least=Threshold.parse(at_least))


class ConvergenceRuleTestCase(_Rules):
    """A mutation converges when any gene it touches was hit in enough ALEs."""

    def test_one_gene_in_two_ales_converges(self):
        first = self.mutation(100); self.observe(self.sample("1"), first)
        second = self.mutation(200); self.observe(self.sample("2"), second)

        self.assertEqual({first.id, second.id}, self.convergent())

    def test_the_same_gene_twice_in_one_ale_does_not(self):
        """Recurrence within a lineage is not convergence, and this is the whole point of
        the analysis -- counting samples rather than ALEs passes everything else and fails
        this."""
        self.observe(self.sample("1", time_point=1), self.mutation(100))
        self.observe(self.sample("1", time_point=2), self.mutation(200))

        self.assertEqual(set(), self.convergent())

    def test_a_different_gene_in_the_other_ale_does_not(self):
        self.observe(self.sample("1"), self.mutation(100, "geneA"))
        self.observe(self.sample("2"), self.mutation(200, "geneB"))

        self.assertEqual(set(), self.convergent())

    def test_an_intergenic_mutation_is_answered_once_and_one_shared_gene_is_enough(self):
        """It touches two genes: one entry, not one per gene, and *any* shared gene
        qualifies it -- thrB is in one ALE only."""
        intergenic = self.mutation(100, "thrA, thrB"); self.observe(self.sample("1"), intergenic)
        other = self.mutation(200, "thrA"); self.observe(self.sample("2"), other)

        self.assertEqual({intergenic.id, other.id}, self.convergent())

    def test_an_unannotated_mutation_shares_no_gene(self):
        """Two mutations with no gene must not converge on the empty name."""
        self.observe(self.sample("1"), self.mutation(100, ""))
        self.observe(self.sample("2"), self.mutation(200, ""))

        self.assertEqual(set(), self.convergent())

    def test_the_threshold_counts_populations(self):
        genes = [self.mutation(100 * n) for n in (1, 2, 3)]
        for n, mutation in enumerate(genes, start=1):
            self.observe(self.sample(str(n)), mutation)
        ids = {m.id for m in genes}

        self.assertEqual(ids, self.convergent("3"))
        self.assertEqual(set(), self.convergent("4"))
        self.assertEqual(ids, self.convergent("100%"))
        self.assertEqual(ids, self.convergent("50%"), "half of three is two, which thrA has")

    def test_the_readers_ignored_gene_is_gone_before_the_question(self):
        """The filter is applied upstream, to the calls the rows are built from, so an
        ignored gene contributes no ALE -- otherwise it could make something else look
        convergent."""
        self.observe(self.sample("1"), self.mutation(100))
        self.observe(self.sample("2"), self.mutation(200))

        self.assertEqual(set(), self.convergent(view_filter=ViewFilter.parse(genes="thrA")))

    def test_a_partly_ignored_intergenic_mutation_survives(self):
        """Subset, not intersection: ignoring one of its two genes hides nothing."""
        intergenic = self.mutation(100, "thrA, thrB"); self.observe(self.sample("1"), intergenic)
        self.observe(self.sample("2"), self.mutation(200, "thrA, thrB"))

        self.assertIn(intergenic.id, self.convergent(view_filter=ViewFilter.parse(genes="thrA")))


class FixationRuleTestCase(_Rules):
    """A mutation is fixed in an ALE when present at both of its last two sampled time
    points, and qualifies when that holds in enough ALEs."""

    def setUp(self):
        super().setUp()
        self.t1 = self.sample("99", time_point=1)
        self.t2 = self.sample("99", time_point=2)

    def test_nothing_fixes_when_nothing_stays(self):
        self.observe(self.t1, self.mutation(1, "geneA"))
        self.observe(self.t2, self.mutation(2, "geneB"))
        self.observe(self.t2, self.mutation(3, "geneB"))

        self.assertEqual(set(), self.fixed())

    def test_a_mutation_in_both_of_the_last_two_time_points_is_fixed(self):
        stays = self.mutation(1, "geneA")
        self.observe(self.t1, stays); self.observe(self.t2, stays)
        self.observe(self.t2, self.mutation(2, "geneB"))

        self.assertEqual({stays.id}, self.fixed())

    def test_a_mutation_that_was_lost_is_not(self):
        """Fixed up to the second time point and gone by the third: only the *last two*
        are consulted, so this is not fixed."""
        t3 = self.sample("99", time_point=3)
        lost = self.mutation(1, "geneA")
        self.observe(self.t1, lost); self.observe(self.t2, lost)
        self.observe(t3, self.mutation(3, "geneC"))

        self.assertEqual(set(), self.fixed())

    def test_the_last_two_sampled_time_points_not_consecutive_numbers(self):
        far = self.sample("99", time_point=30000)
        stays = self.mutation(1, "geneA")
        self.observe(self.t2, stays); self.observe(far, stays)

        self.assertEqual({stays.id}, self.fixed())

    def test_an_ale_sampled_once_can_never_fix_anything(self):
        only = self.sample("1", time_point=500)
        self.observe(only, self.mutation(1, "geneA"))

        self.assertEqual(set(), self.fixed())

    def test_a_time_point_every_call_was_filtered_out_of_is_still_the_last(self):
        """The time axis comes from the samples, not the calls. Hide the last time point's
        only call and the mutation present at the two before it has not fixed."""
        t3 = self.sample("99", time_point=3)
        early = self.mutation(1, "geneA")
        self.observe(self.t1, early); self.observe(self.t2, early)
        MutationCall.objects.create(sample=t3, mutation=self.mutation(3, "geneC"),
                                    present=True, frequency=0.1)

        self.assertEqual(set(), self.fixed(view_filter=ViewFilter.parse(min_freq="50")))

    def test_the_readers_ignored_gene_is_gone_before_the_question(self):
        stays = self.mutation(1, "geneA")
        self.observe(self.t1, stays); self.observe(self.t2, stays)

        self.assertEqual(set(), self.fixed(view_filter=ViewFilter.parse(genes="geneA")))

    def test_the_threshold_counts_populations_it_fixed_in(self):
        both = self.mutation(1, "geneA")
        one = self.mutation(2, "geneB")
        for sample in (self.t1, self.t2):
            self.observe(sample, both); self.observe(sample, one)
        for time_point in (1, 2):
            self.observe(self.sample("2", time_point=time_point), both)

        self.assertEqual({both.id, one.id}, self.fixed("1"))
        self.assertEqual({both.id}, self.fixed("2"))
        self.assertEqual({both.id}, self.fixed("100%"))
        self.assertEqual(set(), self.fixed("3"))
