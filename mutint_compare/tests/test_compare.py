"""The Compare page, now that it is a plugin.

These can only run in an assembled project. mutint-core has no plugin discovery of any kind,
so `./mutint test` cannot reach this file -- run it as `./mutint test mutint_compare`.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from mutint_experiment.models import (
    Experiment, Population, Project,
)
from mutint_sample.models import Mutation, MutationCall, Sample

PAGE = "/compare/"


class CompareTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="owner", email="o@e.com", is_active=True)
        self.client.force_login(self.user)
        # Through the view: Project.objects.create leaves the owner without the guardian
        # grant, and get_experiment then refuses the page.
        created = self.client.post(
            "/project/create/", {"name": "P", "experiment": "E"}).json()
        self.experiment = Experiment.objects.get(pk=created["experiment_id"])

        from mutint_import.gd_import import prepare_experiment_by_id
        context = prepare_experiment_by_id(self.experiment.id)
        ale = Population.objects.create(experiment=self.experiment, name=1)
        self.sample = Sample.objects.create(
            population=ale, time_point=30000, name="1-1", is_clonal=True,
            source_name="1-30000-1-1")
        # `gene` must not be null: the builder hands it to mutint_common.util.get_gene_list,
        # which splits it unguarded. The column is nullable, so that is a trap rather than
        # a fixture detail -- but it is pre-existing and shared by every table page.
        self.mutation = Mutation.objects.create(
            mutation_type="SNP", start_position=1000, sequence_change="A>T",
            gene="thrA", experiment=self.experiment)
        MutationCall.objects.create(
            sample=self.sample, mutation=self.mutation,
            present=True, frequency=0.5)

    def _get(self, **params):
        params.setdefault("experiment_id", self.experiment.id)
        return self.client.get(PAGE, params)

    def test_the_page_renders_the_experiment(self):
        response = self._get()

        self.assertEqual(200, response.status_code)
        html = response.content.decode()
        self.assertIn("Compare", html)
        # The column is labeled by label, which prefers the isolate
        # description and falls back to the coordinate -- not by sample_name.
        self.assertIn("1 / 30000 / 1-1", html)

    def test_the_show_menu_offers_convergent_and_fixed(self):
        """The two sets are always offered, counted, even when empty -- one sample fixes
        nothing and converges with nothing."""
        html = self._get().content.decode()
        self.assertIn('data-role="show"', html)
        self.assertIn("Convergent (0)", html)
        self.assertIn("Fixed (0)", html)

    def test_the_thresholds_are_in_the_form_and_remembered(self):
        html = self._get(convergent_min="3", fixed_min="50%").content.decode()
        self.assertRegex(html, r'name="convergent_min"[^>]*value="3"')
        self.assertRegex(html, r'name="fixed_min"[^>]*value="50%"')
        # The sidebar's link carries no parameters; the page comes back as it was left.
        again = self._get().content.decode()
        self.assertIn('value="3"', again)
        self.assertIn('value="50%"', again)
        self.assertRegex(again, r"at least 3 of the\s+1 population shown")

    def test_it_is_reachable_by_name(self):
        """The nav entry and breseq_table's link both reverse 'compare' rather than
        hardcoding a path, so the name is part of the contract."""
        from django.urls import reverse

        self.assertEqual(PAGE, reverse("compare"))

    def test_it_registers_a_nav_entry(self):
        from mutint_common.nav_registry import EXPERIMENT_SECTION, get_nav_items

        labels = [item["label"] for item in get_nav_items(EXPERIMENT_SECTION)]
        self.assertIn("Compare", labels)

    def test_the_per_sample_page_links_here(self):
        """Core renders that link only when this route resolves, so with the plugin
        installed it must be present."""
        html = self.client.get(
            "/mutations/breseq", {"experiment_id": self.experiment.id}
        ).content.decode()

        self.assertIn(PAGE, html)
        self.assertIn("all samples", html)

    def test_it_renders_the_readers_own_filter_controls(self):
        """Two tests stood here: one that this page owned a `Show Experiment Filtered`
        checkbox, and one that Fixation and Converge did *not* render it -- it was gated on a
        flag only this view set, because it had rendered inert on the pages that never read it
        back.

        Both are gone with the checkbox. It offered to see through the *shared* filter, which
        is not a question a reader has about their own, and the controls gate themselves on
        having an experiment rather than on a flag each page must remember. So the assertion
        inverts: every page sharing this template gets working controls."""
        html = self._get().content.decode()

        self.assertIn('name="min_freq"', html)
        self.assertIn('name="ignore_genes"', html)
        self.assertNotIn('name="show_exp_filtered"', html)
        self.assertNotIn('name="show_global_filtered"', html)

    def test_the_retired_pages_are_gone(self):
        """Fixed Mutations and Converged Mutations were pages of their own and are the Show
        menu now; this used to fetch /fixation to check it rendered the filter too."""
        for path in ("/fixation/", "/converge/"):
            with self.subTest(path=path):
                response = self.client.get(path, {"experiment_id": self.experiment.id})
                self.assertEqual(404, response.status_code)

    def test_the_table_is_the_mutation_matrix(self):
        """Core's matrix, with this experiment's samples as columns and the two menus.

        Nothing of the old table survives here: no tag endpoints, no tag menus, no colvis
        button. Tagging left Compare when the matrix arrived -- the page reads, the editor
        writes.
        """
        html = self._get().content.decode()

        self.assertIn("data-mutation-matrix", html)
        self.assertIn('<th class="breseq-sample sample-palette-0"', html)
        self.assertIn("1 / 30000 / 1-1", html)
        self.assertIn('data-role="columns"', html)
        self.assertIn('data-role="samples"', html)
        self.assertIn("mutation_matrix.js", html)
        self.assertNotIn("toggle-mut-tag", html)
        self.assertNotIn("toggle-rep-tag", html)
        self.assertNotIn("fa-tags", html)
        self.assertNotIn("add_to_exp_filter", html)

    def test_no_experiment_selected_is_explained(self):
        response = self.client.get(PAGE)

        self.assertEqual(200, response.status_code)
        self.assertIn("Select an experiment", response.content.decode())

    def test_a_project_you_cannot_view_is_refused(self):
        stranger = User.objects.create(username="stranger", email="s@e.com", is_active=True)
        self.client.force_login(stranger)

        html = self._get().content.decode()

        self.assertNotIn("1 / 30000 / 1-1", html)

    # --- a mutation nobody called ---------------------------------------------------------
    #
    # Core covers `build_matrix` directly, but this is the table people actually
    # read an experiment from, and it is the reason the gap mattered: a mutation added
    # through /curate/add was stored, listed on the editor's own per-sample page,
    # and absent here -- which reads as the add having silently failed.

    def _add_by_hand(self, position=7777):
        
        from mutint_curate.record_builder import build_call

        mutation = Mutation.objects.create(
            mutation_type="SNP", start_position=position, sequence_change="C>G",
            gene="ilvG", experiment=self.experiment)
        MutationCall.objects.create(
            sample=self.sample, mutation=mutation,
            **build_call(1.0))
        return mutation

    def test_a_hand_added_mutation_has_a_row_on_the_compare_page(self):
        self._add_by_hand()

        html = self._get().content.decode("utf-8")

        self.assertIn("7,777", html)
        self.assertIn("ilvG", html)

    def test_the_called_mutation_is_still_there_beside_it(self):
        """The fix widened what renders; it must not have swapped one rule for another that
        drops what the old one caught."""
        self._add_by_hand()

        html = self._get().content.decode("utf-8")

        self.assertIn("1,000", html)
        self.assertIn("thrA", html)
