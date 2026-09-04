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

from aledb_experiment.models import Experiment
from aledb_sample.models import Mutation
from aledb_experiment import paths

DATASET = "aledb-compare-example"


class ExampleDatasetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create(username="admin", email="a@e.com",
                            is_active=True, is_superuser=True)
        call_command("load_example", DATASET, stdout=StringIO(), stderr=StringIO())
        cls.experiment = Experiment.objects.get(name=DATASET)

    def test_it_covers_six_mutation_types(self):
        """Compare is the only page that renders them all. /mutations/amplifications was
        once the only place AMP appeared, because Compare passed a `filter_type` whose
        value means *exclude*; the AMP row is what stops that returning unnoticed."""
        types = set(Mutation.objects.filter(experiment=self.experiment)
                    .values_list("mutation_type", flat=True))

        self.assertEqual({"SNP", "SUB", "INS", "DEL", "MOB", "AMP"}, types)

    def test_the_grid_is_two_lineages_by_three_flasks(self):
        from aledb_sample.models import Sample

        samples = Sample.objects.filter(
            **{paths.to_experiment(): self.experiment})

        self.assertEqual(6, samples.count())
        # The ALE is text and the flask a number -- `aledb_experiment.0008`, which is also
        # why a lineage can be called `Ara-1` rather than 1.
        self.assertEqual({("1", 100), ("1", 200), ("1", 300),
                          ("2", 100), ("2", 200), ("2", 300)},
                         {(s.population_name, s.time_point_value) for s in samples})

    def test_one_sample_is_a_population(self):
        """Its cells show a frequency where the clonal ones show a check -- the difference
        the cell rendering exists to make."""
        from aledb_sample.models import Sample

        populations = Sample.objects.filter(
            **{paths.to_experiment(): self.experiment,
               **paths.mixed_filter()})

        self.assertEqual(1, populations.count())
        self.assertEqual(("1", 300),
                         (populations.first().population_name, populations.first().time_point_value))

    def test_the_pattern_spans_full_partial_and_single_rows(self):
        """A table where every row looks the same demonstrates nothing."""
        from aledb_sample.models import MutationCall

        spread = {}
        for mutation in Mutation.objects.filter(experiment=self.experiment):
            spread[(mutation.mutation_type, mutation.position)] = (
                MutationCall.objects.filter(mutation=mutation).count())

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
        cls.experiment = Experiment.objects.get(name=DATASET)

    def setUp(self):
        self.client.force_login(self.owner)

    def _html(self):
        return self.client.get("/compare/",
                               {"experiment_id": self.experiment.id}).content.decode()

    def test_every_sample_is_a_column(self):
        html = self._html()
        for ale in (1, 2):
            for flask in (100, 200, 300):
                with self.subTest(ale=ale, flask=flask):
                    self.assertIn("%d / %d / 1-1" % (ale, flask), html)

    def test_the_population_sample_is_a_column(self):
        """Compare passes all four arguments to get_reseq_ordered_dict, unlike the two
        plugin pages that used to drop population samples."""
        self.assertIn("1 / 300 / 1-1", self._html())

    def test_the_amplification_reaches_the_table(self):
        """AMP is a first-class breseq type and this is the only page that shows it."""
        self.assertIn("AMP", self._html())

    def test_the_genes_reach_the_table(self):
        html = self._html()

        self.assertIn("thrA", html)
        self.assertIn("araJ", html)
