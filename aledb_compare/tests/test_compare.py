"""The Compare page, now that it is a plugin.

These can only run in an assembled project. aledb-core has no plugin discovery of any kind,
so `./aledb test` cannot reach this file -- run it as `./mutint test aledb_compare`. That is
already true of aledb-fixation and aledb-converge.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from aledb_experiment.models import (
    Experiment, Population, TimePoint, Project,
)
from aledb_seq.models import Mutation, ObservedMutation, Sample

PAGE = "/compare/"


class CompareTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="owner", email="o@e.com", is_active=True)
        self.client.force_login(self.user)
        # Through the view: Project.objects.create leaves the owner without the guardian
        # grant, and get_ale_experiment then refuses the page.
        created = self.client.post(
            "/ale/projects/create/", {"name": "P", "experiment": "E"}).json()
        self.experiment = Experiment.objects.get(pk=created["experiment_id"])

        from aledb_import.gd_import import prepare_experiment_by_id
        context = prepare_experiment_by_id(self.experiment.id)
        ale = Population.objects.create(experiment=self.experiment, name=1)
        flask = TimePoint.objects.create(population=ale, value=30000, media=context["media"])
        self.sample = Sample.objects.create(
            time_point=flask, name="1-1", is_clonal=True,
            source_name="1-30000-1-1")
        # `gene` must not be null: the builder hands it to aledb_common.util.get_gene_list,
        # which splits it unguarded. The column is nullable, so that is a trap rather than
        # a fixture detail -- but it is pre-existing and shared by every table page.
        self.mutation = Mutation.objects.create(
            mutation_type="SNP", position=1000, sequence_change="A>T",
            gene="thrA", experiment=self.experiment)
        ObservedMutation.objects.create(
            sample=self.sample, mutation=self.mutation,
            present=True, frequency=0.5)

    def _get(self, **params):
        params.setdefault("ale_experiment_id", self.experiment.id)
        return self.client.get(PAGE, params)

    def test_the_page_renders_the_experiment(self):
        response = self._get()

        self.assertEqual(200, response.status_code)
        html = response.content.decode()
        self.assertIn("Compare", html)
        # The column is labelled by ale_flask_isolate_str, which prefers the isolate
        # description and falls back to the coordinate -- not by sample_name.
        self.assertIn("A1 F30000 I1-1", html)

    def test_it_is_reachable_by_name(self):
        """The nav entry and breseq_table's link both reverse 'compare' rather than
        hardcoding a path, so the name is part of the contract."""
        from django.urls import reverse

        self.assertEqual(PAGE, reverse("compare"))

    def test_it_registers_a_nav_entry(self):
        from aledb_common.nav_registry import EXPERIMENT_SECTION, get_nav_items

        labels = [item["label"] for item in get_nav_items(EXPERIMENT_SECTION)]
        self.assertIn("Compare", labels)

    def test_the_per_sample_page_links_here(self):
        """Core renders that link only when this route resolves, so with the plugin
        installed it must be present."""
        html = self.client.get(
            "/mutations/breseq", {"ale_experiment_id": self.experiment.id}
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

    def test_the_other_tables_render_them_too(self):
        # follow=True: /fixation is an APPEND_SLASH redirect, and an unfollowed GET returns
        # an empty body -- which is why the assertNotIn this replaced passed without ever
        # looking at the page.
        html = self.client.get(
            "/fixation", {"ale_experiment_id": self.experiment.id}, follow=True
        ).content.decode()

        self.assertIn('name="min_freq"', html)

    def test_the_shared_table_actions_are_reversed_not_hardcoded(self):
        """table_template.js reverses the tag endpoints by name. If it went back to
        literals, this page would still work and Search would silently break, so the
        assertion is on the rendered URL rather than on behaviour.

        Two endpoints, not three. `add_to_exp_filter` was the third: it appended a mutation id
        to `AleExperimentFilter.ignored_mutations` so the row would stop being drawn -- a
        delete that kept the row, per experiment and unattributed. aledb-core's
        `aledb_mutation_editor` replaces it.
        """
        html = self._get().content.decode()

        self.assertIn("/mutation-table/toggle-mut-tag/", html)
        self.assertIn("/mutation-table/toggle-rep-tag", html)
        self.assertNotIn("/mutations/toggle-mut-tag", html)
        self.assertNotIn("add_to_exp_filter", html)

    def test_no_experiment_selected_is_explained(self):
        response = self.client.get(PAGE)

        self.assertEqual(200, response.status_code)
        self.assertIn("Select an experiment", response.content.decode())

    def test_a_project_you_cannot_view_is_refused(self):
        stranger = User.objects.create(username="stranger", email="s@e.com", is_active=True)
        self.client.force_login(stranger)

        html = self._get().content.decode()

        self.assertNotIn("A1 F30000 I1-1", html)

    # --- a mutation nobody called ---------------------------------------------------------
    #
    # Core covers `get_mutation_table_body` directly, but this is the table people actually
    # read an experiment from, and it is the reason the gap mattered: a mutation added
    # through /mutation-editor/add was stored, listed on the editor's own per-sample page,
    # and absent here -- which reads as the add having silently failed.

    def _add_by_hand(self, position=7777):
        from decimal import Decimal

        from aledb_mutation_editor.record_builder import build_observation

        mutation = Mutation.objects.create(
            mutation_type="SNP", position=position, sequence_change="C>G",
            gene="ilvG", experiment=self.experiment)
        ObservedMutation.objects.create(
            sample=self.sample, mutation=mutation,
            **build_observation(Decimal("1.0")))
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
