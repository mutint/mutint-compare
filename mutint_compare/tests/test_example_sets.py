"""The convergence and fixation example datasets, and the answers they were built to have.

Each README states its answer as a table; these assert it through the page, reading the
rows the matrix hands the browser. An empty set is otherwise indistinguishable from a
correct one, and that ambiguity is what once made fixation look broken for as long as it did.

Runs only in an assembled project: `./mutint test mutint_compare`.
"""

import html
import json
import re
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from mutint_experiment import paths
from mutint_experiment.models import Experiment, Population
from mutint_sample.models import Sample

CONVERGENCE = "mutint-compare-convergence-example"
FIXATION = "mutint-compare-fixation-example"
ROWS = re.compile(r'<script id="mutation-matrix-rows" type="application/json">(.*?)</script>', re.S)


class _ExamplePage(TestCase):
    dataset = None

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="admin", email="a@e.com",
                                        is_active=True, is_superuser=True)
        call_command("load_example", cls.dataset, stdout=StringIO(), stderr=StringIO())
        cls.experiment = Experiment.objects.get(name=cls.dataset)

    def setUp(self):
        self.client.force_login(self.owner)

    def html(self, **params):
        params.setdefault("experiment_id", self.experiment.id)
        return self.client.get("/compare/", params).content.decode()

    def rows(self, **params):
        return json.loads(ROWS.search(self.html(**params)).group(1))

    def in_set(self, key, **params):
        """`{(gene, position)}` of the rows in the set: the gene name alone, since the cell
        is breseq's HTML with a strand arrow after the name."""
        return {(html.unescape(re.sub("<[^>]+>", "", row["gene"])).split("\xa0")[0].strip(),
                 row["position_sort"])
                for row in self.rows(**params) if key in row.get("sets", [])}


class ConvergenceExampleTestCase(_ExamplePage):
    dataset = CONVERGENCE

    def test_three_lineages_landed(self):
        """Convergence counts ALEs, so the dataset is only meaningful if they are distinct."""
        self.assertEqual({"1", "2", "3"},
                         {a.name for a in Population.objects.filter(experiment=self.experiment)})

    def test_the_answer_is_exactly_these_four(self):
        """thrA at *different* positions in ALE 1 and ALE 2 -- the gene converges, not the
        mutation, and both are listed; divB in ALE 1 and 3; araJ in *both* of ALE 3's flasks
        is recurrent and still one lineage; pseuA once."""
        self.assertEqual({("thrA", 150), ("thrA", 200), ("divB", 2200), ("divB", 2300)},
                         self.in_set("convergent"))

    def test_the_show_menu_counts_it(self):
        html = self.html()
        self.assertIn("Convergent (4)", html)
        self.assertIn("Fixed (", html)

    def test_the_threshold_changes_the_answer(self):
        self.assertEqual(set(), self.in_set("convergent", convergent_min="3"))
        self.assertEqual({("thrA", 150), ("thrA", 200), ("divB", 2200), ("divB", 2300)},
                         self.in_set("convergent", convergent_min="50%"),
                         "half of three populations is two")
        self.assertEqual(set(), self.in_set("convergent", convergent_min="100%"))

    def test_every_lineage_is_a_column(self):
        html = self.html()
        for ale in (1, 2, 3):
            with self.subTest(ale=ale):
                self.assertIn("%d / 100 / 1-1" % ale, html)


class FixationExampleTestCase(_ExamplePage):
    dataset = FIXATION

    def test_the_time_axis_is_the_time_point(self):
        """The whole precondition: a filename that is not strict A-F-I-R falls to
        auto-numbering, one time point per ALE, and nothing can fix."""
        per_ale = {}
        rows = (Sample.objects.filter(**{paths.to_experiment(): self.experiment})
                .values_list(paths.to_population_label(), paths.to_time_point_value()))
        for population_name, time_point in rows:
            per_ale.setdefault(population_name, set()).add(time_point)
        self.assertEqual({"1": {500, 1000, 1500, 2000}, "2": {500, 1000, 1500, 2000}}, per_ale)

    def test_the_answer_is_exactly_these_three(self):
        """thrA arrives and stays in ALE 1; divB is present throughout both; thrB arrives
        and stays in ALE 2. araJ was lost, pseuA arrived only at the end."""
        self.assertEqual({("thrA", 150), ("divB", 2200), ("thrB", 600)}, self.in_set("fixed"))

    def test_fixation_is_decided_per_lineage_and_the_threshold_counts_them(self):
        """thrA fixed in ALE 1 only and seen once in ALE 2; at two populations only divB
        survives."""
        self.assertEqual({("divB", 2200)}, self.in_set("fixed", fixed_min="2"))
        self.assertEqual({("divB", 2200)}, self.in_set("fixed", fixed_min="100%"))

    def test_the_population_sample_is_a_column(self):
        """ALE 1's last flask is a population sample; the old pages dropped those."""
        self.assertIn("1 / 2000 / 1-1", self.html())

    def test_the_same_data_has_a_convergent_gene(self):
        self.assertIn(("thrA", 150), self.in_set("convergent"))
