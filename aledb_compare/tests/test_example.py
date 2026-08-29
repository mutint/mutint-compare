"""The shipped example dataset.

Compare computes nothing, so unlike fixation and converge there is no derived answer to
check. What is worth asserting is that the *pattern* survives into the page: a row present
in every sample, a row in one, every mutation type, and a population sample whose cells read
as a frequency. `examples/compare/README.md` states the layout.

Runs only in an assembled project: `./mutint test aledb_compare`.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from aledb_experiment.models import AleExperiment
from aledb_seq.models import Mutation

DATASET = "aledb-compare-example"


class ExampleDatasetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create(username="admin", email="a@e.com",
                            is_active=True, is_superuser=True)
        call_command("load_example", DATASET, stdout=StringIO(), stderr=StringIO())
        cls.experiment = AleExperiment.objects.get(name=DATASET)

    def test_it_covers_six_mutation_types(self):
        """Compare is the only page that renders them all. /mutations/amplifications was
        once the only place AMP appeared, because Compare passed a `filter_type` whose
        value means *exclude*; the AMP row is what stops that returning unnoticed."""
        types = set(Mutation.objects.filter(ale_experiment=self.experiment)
                    .values_list("mutation_type", flat=True))

        self.assertEqual({"SNP", "SUB", "INS", "DEL", "MOB", "AMP"}, types)

    def test_the_grid_is_two_lineages_by_three_flasks(self):
        from aledb_seq.models import ResequencingExperiment

        samples = ResequencingExperiment.objects.filter(
            tech_rep__isolate__flask__ale_id__ale_experiment=self.experiment)

        self.assertEqual(6, samples.count())
        # The ALE is text and the flask a number -- `aledb_experiment.0008`, which is also
        # why a lineage can be called `Ara-1` rather than 1.
        self.assertEqual({("1", 100), ("1", 200), ("1", 300),
                          ("2", 100), ("2", 200), ("2", 300)},
                         {(s.ale_id, s.flask_number) for s in samples})

    def test_one_sample_is_a_population(self):
        """Its cells show a frequency where the clonal ones show a check -- the difference
        the cell rendering exists to make."""
        from aledb_seq.models import ResequencingExperiment

        populations = ResequencingExperiment.objects.filter(
            tech_rep__isolate__flask__ale_id__ale_experiment=self.experiment,
            tech_rep__isolate__is_population=True)

        self.assertEqual(1, populations.count())
        self.assertEqual(("1", 300),
                         (populations.first().ale_id, populations.first().flask_number))

    def test_the_pattern_spans_full_partial_and_single_rows(self):
        """A table where every row looks the same demonstrates nothing."""
        from aledb_seq.models import ObservedMutation

        spread = {}
        for mutation in Mutation.objects.filter(ale_experiment=self.experiment):
            spread[(mutation.mutation_type, mutation.position)] = (
                ObservedMutation.objects.filter(mutation=mutation).count())

        self.assertEqual(6, spread[("SNP", 150)], "present in every sample")
        self.assertEqual(3, spread[("DEL", 1450)], "one lineage, all its flasks")
        self.assertEqual(2, spread[("INS", 2250)], "the last flask of each lineage")
        self.assertEqual(1, spread[("MOB", 1300)], "a single sample")


class ExamplePageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="admin", email="a@e.com",
                                        is_active=True, is_superuser=True)
        call_command("load_example", DATASET, stdout=StringIO(), stderr=StringIO())
        cls.experiment = AleExperiment.objects.get(name=DATASET)

    def setUp(self):
        self.client.force_login(self.owner)

    def _html(self):
        return self.client.get("/compare/",
                               {"ale_experiment_id": self.experiment.ale_id}).content.decode()

    def test_every_sample_is_a_column(self):
        html = self._html()
        for ale in (1, 2):
            for flask in (100, 200, 300):
                with self.subTest(ale=ale, flask=flask):
                    self.assertIn("A%d F%d I1 R1" % (ale, flask), html)

    def test_the_population_sample_is_a_column(self):
        """Compare passes all four arguments to get_reseq_ordered_dict, unlike the two
        plugin pages that used to drop population samples."""
        self.assertIn("A1 F300 I1 R1", self._html())

    def test_the_amplification_reaches_the_table(self):
        """AMP is a first-class breseq type and this is the only page that shows it."""
        self.assertIn("AMP", self._html())

    def test_the_genes_reach_the_table(self):
        html = self._html()

        self.assertIn("thrA", html)
        self.assertIn("araJ", html)
