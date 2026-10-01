"""The cross-sample mutation table: the experiment's mutations down, its samples across.

The page is core's **mutation matrix** -- `mutint_sample.mutation_matrix.build_matrix` and
`mutation_matrix/page.html`, extended by `compare/page.html` -- with every call the experiment
holds as its rows. What is Compare's own is the two **row sets** it offers, Convergent and
Fixed, with the thresholds that decide them.

**Everything is decided in the browser.** The view sends every sample, every call unfiltered,
and the designated ancestor's mutations flagged; the page applies the reader's filter, hides
samples by population, treatment, type and time, draws or drops the ancestral rows, and
computes the two sets over what is shown -- `static/mutint_compare/compare_sets.js`, a port
of `analysis.py` held to it by `tests/test_sets_js.py`. So hiding a population changes what
converged, at once, which is what a reader looking at the table expects.
"""

import logging
import time

from django.http import HttpResponse
from django.template import loader

import mutint_sample.views.common
from mutint_common.logger import join_extras, user_extra
from mutint_common.util import get_user_context
from mutint_experiment import models
from mutint_experiment.ancestor import ancestral_mutation_ids, ancestral_shown, describe_ancestor
from mutint_filter.view_filter import get_view_filter
from mutint_filter.views import filter_json
from mutint_sample.mutation_matrix import ClientSet, build_matrix
from mutint_sample.util import get_all_calls_filtered, get_ordered_sample_dict

from mutint_compare import analysis

logger = logging.getLogger(__name__)


def mutation_table(request):
    logger.info("mutation usage", extra=user_extra(request))
    context = get_user_context(request.user)
    try:
        start_time = time.time()
        experiment = mutint_sample.views.common.get_experiment(request)

        # Every sample and every call, unfiltered, the ancestor's rows included and flagged:
        # which samples show, which frequencies count, whether the ancestral rows are drawn and
        # what is convergent or fixed are all decided in the browser, so changing any of them
        # costs no round trip. The ancestor itself has no column: `sample_dict` leaves it out.
        sample_dict = get_ordered_sample_dict(experiment.id)
        calls = get_all_calls_filtered(experiment.id, include_ancestral=True)
        matrix = build_matrix(calls, sample_dict, experiment=experiment,
                              client_sets=(ClientSet("convergent", "Convergent"),
                                           ClientSet("fixed", "Fixed")),
                              ancestral_mutation_ids=ancestral_mutation_ids(experiment.id),
                              csv_title="%s_ExpID%d" % (experiment.name, experiment.id))

        context.update({
            "experiment_name": experiment.name,
            "experiment_id": experiment.id,
            "project_name": experiment.project.name,
            "project_id": experiment.project.id,
            "title": experiment.name + " Mutations",
            "template_header": "Compare",
            "matrix": matrix,
            "empty_message": "No mutations to show for these samples and this filter.",
            # Where the browser starts: the reader's filter and the ancestral choice, both
            # from the session, and both written back there through `/filter/set`.
            "view_filter_state": filter_json(get_view_filter(request, experiment.id)),
            "ancestor": describe_ancestor(experiment.id),
            "ancestral_shown": ancestral_shown(request, experiment.id),
            "default_thresholds": analysis.Thresholds().as_dict(),
        })
        logger.info("mutation performance", extra=join_extras(
            user_extra(request), {"time taken": time.time() - start_time}))
        return HttpResponse(loader.get_template("compare/page.html").render(context, request),
                            content_type="text/html")
    except models.Experiment.DoesNotExist:
        return mutint_sample.views.common.no_experiment_selected(
            request, context, logger, "mutation table")
    except Exception as e:
        logger.exception("mutations broke", extra=user_extra(request))
        template = loader.get_template("500.html")
        context['err_message'] = str(e)
        return HttpResponse(template.render(context, request), content_type="text/html")
