"""The Compare page, now that it is a plugin.

These can only run in an assembled project. aledb-core has no plugin discovery of any kind,
so `./aledb test` cannot reach this file -- run it as `./mutint test aledb_compare`. That is
already true of aledb-fixation and aledb-converge.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from aledb_experiment.models import (
    AleExperiment, AleId, Flask, Isolate, Project, TechnicalReplicate,
)
from aledb_seq.models import Mutation, ObservedMutation, ResequencingExperiment

PAGE = "/compare/"


class CompareTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="owner", email="o@e.com", is_active=True)
        self.client.force_login(self.user)
        # Through the view: Project.objects.create leaves the owner without the guardian
        # grant, and get_ale_experiment then refuses the page.
        created = self.client.post(
            "/ale/projects/create/", {"name": "P", "experiment": "E"}).json()
        self.experiment = AleExperiment.objects.get(pk=created["experiment_id"])

        from aledb_import.gd_import import prepare_experiment_by_id
        context = prepare_experiment_by_id(self.experiment.ale_id)
        ale = AleId.objects.create(ale_experiment=self.experiment, ale_id=1)
        flask = Flask.objects.create(ale_id=ale, flask_number=30000, media=context["media"])
        isolate = Isolate.objects.create(flask=flask, isolate_number=1, is_population=False,
                                         freezer_box=context["freezer_box"])
        tech_rep = TechnicalReplicate.objects.create(isolate=isolate, tech_rep_number=1)
        self.sample = ResequencingExperiment.objects.create(
            tech_rep=tech_rep, sample_name="1-30000-1-1")
        # `gene` must not be null: the builder hands it to aledb_common.util.get_gene_list,
        # which splits it unguarded. The column is nullable, so that is a trap rather than
        # a fixture detail -- but it is pre-existing and shared by every table page.
        self.mutation = Mutation.objects.create(
            mutation_type="SNP", position=1000, sequence_change="A>T",
            gene="thrA", ale_experiment=self.experiment)
        ObservedMutation.objects.create(
            sequencing_experiment=self.sample, mutation=self.mutation,
            present=True, frequency=0.5)

    def _get(self, **params):
        params.setdefault("ale_experiment_id", self.experiment.ale_id)
        return self.client.get(PAGE, params)

    def test_the_page_renders_the_experiment(self):
        response = self._get()

        self.assertEqual(200, response.status_code)
        html = response.content.decode()
        self.assertIn("Compare", html)
        # The column is labelled by ale_flask_isolate_str, which prefers the isolate
        # description and falls back to the coordinate -- not by sample_name.
        self.assertIn("A1 F30000 I1 R1", html)

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
            "/mutations/breseq", {"ale_experiment_id": self.experiment.ale_id}
        ).content.decode()

        self.assertIn(PAGE, html)
        self.assertIn("all samples", html)

    def test_it_owns_the_show_filtered_checkbox(self):
        """base_table_template.html renders it only for a page that sets
        show_filter_toggles -- this one. Fixation, Converge and Search do not.

        There were two of these until the site-wide filter was removed; the surviving one
        reveals what the experiment's own filter hides, for this reader and this request."""
        html = self._get().content.decode()

        self.assertIn('name="show_exp_filtered"', html)
        self.assertNotIn('name="show_global_filtered"', html)

    def test_the_other_tables_do_not_render_them(self):
        html = self.client.get(
            "/fixation", {"ale_experiment_id": self.experiment.ale_id}
        ).content.decode()

        self.assertNotIn('name="show_exp_filtered"', html)

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

        self.assertNotIn("A1 F30000 I1 R1", html)

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
            gene="ilvG", ale_experiment=self.experiment)
        ObservedMutation.objects.create(
            sequencing_experiment=self.sample, mutation=mutation,
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
