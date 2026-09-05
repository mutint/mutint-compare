import os

from django.apps import AppConfig


class CompareConfig(AppConfig):
    """The cross-sample mutation table.

    Compare lived in mutint-core as `mutint_sample.views.mutations.mutation_table` until it was
    pulled out here. It never belonged there: it is one way of *looking* at an experiment's
    mutations, the same kind of thing mutint-fixation and mutint-converge are, and a deployment
    may reasonably want it gone or want its own in its place. Core keeps everything Compare is
    built from -- the table builder, the shared table template, the tag and filter endpoints --
    because Search and the other two plugins use all of it too.
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
        register_example_dataset(
            'mutint-compare-example',
            os.path.join(os.path.dirname(__file__), 'examples', 'compare'),
            description='Two lineages over three flasks, every mutation type, one population sample.')
