"""Compare draws the ancestor's mutations on request, tinted, and decides nothing by them.

Hidden by default: the page opens on the evolved calls exactly as before. `?ancestral=show`
adds the subtracted rows, marked for the script to tint, with cells for the evolved samples
still carrying them -- while the ancestor itself has no column and neither set holds such a
row, so the Show menu's Convergent and Fixed drop them again. The choice is remembered per
experiment, in the session, shared with the per-sample page.

Runs only in an assembled project: `./mutint test mutint_compare`.
"""

import json
import re

from django.contrib.auth.models import User
from django.test import TestCase

from mutint_experiment.models import Experiment, Population, Project
from mutint_experiment.permissions import set_primary_owner
from mutint_sample.models import Mutation, MutationCall, Sample

ROWS = re.compile(r'<script id="mutation-matrix-rows" type="application/json">(.*?)</script>', re.S)
BUTTON = 'data-role="ancestral-toggle"'


class AncestralDisplayTestCase(TestCase):
    """Two ALEs of two flasks plus an ancestor. `shared` is everywhere, `evolved` in every
    evolved flask -- the fixture of `test_ancestor.py`, on the page."""

    def setUp(self):
        self.owner = User.objects.create(username="owner", email="o@e.com", is_active=True)
        self.client.force_login(self.owner)
        project = Project.objects.create(name="P", user=self.owner)
        set_primary_owner(project, self.owner)
        self.experiment = Experiment.objects.create(name="E", project=project)
        self.ancestor = self.make_sample("0", 1)
        evolved_samples = [self.make_sample(ale, flask) for ale in ("1", "2") for flask in (1, 2)]

        self.shared = self.make_mutation(100, "geneA")
        self.evolved = self.make_mutation(200, "geneB")
        for sample in [self.ancestor] + evolved_samples:
            self.observe(sample, self.shared)
        for sample in evolved_samples:
            self.observe(sample, self.evolved)
        self.experiment.set_ancestor(self.ancestor, self.owner)

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

    def html(self, **params):
        params.setdefault("experiment_id", self.experiment.id)
        return self.client.get("/compare/", params).content.decode()

    def rows(self, **params):
        return {row["id"]: row for row in json.loads(ROWS.search(self.html(**params)).group(1))}


class TestHiddenByDefault(AncestralDisplayTestCase):

    def test_the_ancestral_row_is_absent(self):
        rows = self.rows()
        self.assertNotIn(self.shared.id, rows)
        self.assertIn(self.evolved.id, rows)
        self.assertNotIn("ancestral", rows[self.evolved.id])

    def test_the_page_says_so_and_offers_show(self):
        body = self.html()
        self.assertIn("are hidden", body)
        self.assertIn(BUTTON, body)
        self.assertIn("ancestral=show", body)
        self.assertIn("All (1)", body)
        self.assertNotIn("Rows shaded red", body)


class TestShown(AncestralDisplayTestCase):

    def test_the_ancestral_row_appears_marked(self):
        rows = self.rows(ancestral="show")
        self.assertTrue(rows[self.shared.id]["ancestral"])
        self.assertFalse(rows[self.evolved.id]["ancestral"])

    def test_it_is_in_neither_set(self):
        """The sets were decided over the evolved calls, so the Show menu drops it."""
        rows = self.rows(ancestral="show")
        self.assertEqual([], rows[self.shared.id]["sets"])
        self.assertEqual(["convergent", "fixed"], rows[self.evolved.id]["sets"])

    def test_the_counts_follow(self):
        body = self.html(ancestral="show")
        self.assertIn("All (2)", body)
        self.assertIn("Convergent (1)", body)
        self.assertIn("Fixed (1)", body)

    def test_the_ancestor_has_no_column(self):
        self.assertNotIn('data-sample="%d"' % self.ancestor.id, self.html(ancestral="show"))

    def test_its_cells_are_the_evolved_samples(self):
        row = self.rows(ancestral="show")[self.shared.id]
        self.assertEqual(4, sum(1 for cell in row["samples"] if cell))

    def test_the_page_says_so_and_offers_hide(self):
        body = self.html(ancestral="show")
        self.assertIn("shaded red", body)
        self.assertIn("ancestral=hide", body)
        self.assertIn("Rows shaded red are the designated ancestor", body)

    def test_the_choice_is_remembered(self):
        self.html(ancestral="show")
        self.assertIn(self.shared.id, self.rows())
        self.html(ancestral="hide")
        self.assertNotIn(self.shared.id, self.rows())

    def test_the_thresholds_still_round_trip(self):
        body = self.html(ancestral="show", convergent_min="50%")
        self.assertIn('value="50%"', body)
        self.assertIn("ancestral=hide", body)
        self.assertIn("convergent_min=50%25", body)
