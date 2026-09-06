import os

from django.apps import AppConfig


class CompareConfig(AppConfig):
    """The cross-sample mutation table.

    Compare lived in mutint-core as `mutint_sample.views.mutations.mutation_table` until it was
    pulled out here. It never belonged there: it is one way of *looking* at an experiment's
    mutations, and a deployment may reasonably want it gone or want its own in its place. Core
    keeps everything Compare is built from -- the table builder, the shared table template,
    the tag and filter endpoints -- because Search uses all of it too.

    mutint-fixation and mutint-converge were two more ways of looking, each this page over a
    narrower queryset; they are the Show menu's Convergent and Fixed sets now, computed in
    `analysis.py` with thresholds the reader sets. Their example datasets came with them.
    """

    name = 'mutint_compare'

    def ready(self):
        from django.urls import re_path, include
        from mutint_common.example_registry import register_example_dataset
        from mutint_common.plugin_registry import register_plugin_urlpatterns
        from mutint_common.about_registry import register_about_section
        from mutint_common.nav_registry import (
            EXPERIMENT_SECTION, register_nav_item,
        )
        register_plugin_urlpatterns([
            re_path(r'^compare/', include('mutint_compare.urls')),
        ])
        # url_name rather than a literal path: nav_registry skips an entry whose name will not
        # reverse, so a half-installed plugin cannot leave a dead link in the sidebar. Core's
        # own entries use literals only because several rely on APPEND_SLASH redirects.
        register_nav_item('Compare', url_name='compare', section=EXPERIMENT_SECTION)
        register_about_section(self, name='mutint-compare',
                               template='about/sections/mutint_compare.html')

        # A pivot table is only legible against a pattern -- rows present everywhere,
        # rows in one sample only, and every mutation type. See
        # examples/compare/README.md.
        examples = os.path.join(os.path.dirname(__file__), 'examples')
        register_example_dataset(
            'mutint-compare-example', os.path.join(examples, 'compare'),
            description='Two lineages over three flasks, every mutation type, one population sample.')
        # Each with a known answer, so an empty Show menu is unambiguous. See the READMEs.
        register_example_dataset(
            'mutint-compare-convergence-example', os.path.join(examples, 'convergence'),
            description='Three lineages; one gene hit in two of them, another in one only.')
        register_example_dataset(
            'mutint-compare-fixation-example', os.path.join(examples, 'fixation'),
            description='Two lineages over four flasks; mutations that arrive and stay.')
