"""Compare draws the ancestor's mutations on request, tinted, and decides nothing by them.

The page always carries the ancestor's rows, flagged `ancestral`, with cells for the evolved
samples still carrying them; the ancestor itself has no column. The browser drops them unless
the reader asks -- the Show/Hide button on the Ancestral tab, one choice per experiment in the
session (written through `/filter/set`), shared with the per-sample page -- and leaves them out
of both row sets either way; `test_sets_js.py` covers that half.

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


class TestTheRowsAreAlwaysSent(AncestralDisplayTestCase):

    def test_the_ancestral_row_is_present_and_marked(self):
        rows = self.rows()
        self.assertTrue(rows[self.shared.id]["ancestral"])
        self.assertFalse(rows[self.evolved.id]["ancestral"])

    def test_the_ancestor_has_no_column(self):
        self.assertNotIn('data-sample="%d"' % self.ancestor.id, self.html())

    def test_its_cells_are_the_evolved_samples(self):
        row = self.rows()[self.shared.id]
        self.assertEqual(4, sum(1 for cell in row["samples"] if cell))

    def test_the_toggle_is_on_the_ancestral_tab_and_says_who_the_ancestor_is(self):
        body = self.html()
        self.assertIn('data-tab="ancestral"', body)
        start = body.index('id="mutation_matrix-pane-ancestral"')
        self.assertIn(BUTTON, body[start:body.index('class="tab-pane', start)])
        self.assertIn('data-ancestor-name="%s"' % self.ancestor.label, body)
        self.assertIn('data-ancestral-shown="0"', body)


class TestTheChoiceIsRemembered(AncestralDisplayTestCase):

    def set(self, shown):
        response = self.client.post("/filter/set/", json.dumps(
            {"experiment_id": self.experiment.id, "ancestral": shown}),
            content_type="application/json")
        self.assertEqual(200, response.status_code)

    def test_through_the_endpoint(self):
        self.set(True)
        self.assertIn('data-ancestral-shown="1"', self.html())
        self.set(False)
        self.assertIn('data-ancestral-shown="0"', self.html())

    def test_and_through_the_query_string_the_per_sample_page_uses(self):
        self.html(ancestral="show")
        self.assertIn('data-ancestral-shown="1"', self.html())
