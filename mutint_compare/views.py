"""The cross-sample mutation table: the experiment's mutations down, its samples across.

The page is core's **mutation matrix** -- `mutint_sample.mutation_matrix.build_matrix` and
`mutation_matrix/page.html`, extended by `compare/page.html` -- with this experiment's evolved
calls as its rows. What is Compare's own is the queryset below -- every call the experiment
holds, through the reader's filter, every mutation type included -- and the two **row sets**
it hands the matrix, Convergent and Fixed, with the thresholds that decide them. See
`analysis.py`; mutint-fixation and mutint-converge used to be this page over a narrower
queryset, and the Show menu is where they went.

The designated ancestor's mutations are subtracted from all of that. On request
(`ancestral_shown`, the button in the summary line) the page draws them as well, tinted red,
with cells for the evolved samples still carrying them -- display only, decided after the
sets, so neither set ever holds one.
"""

import logging
import time

from django.http import HttpResponse
from django.template import loader

import mutint_sample.views.common
from mutint_common.logger import join_extras, user_extra
from mutint_common.util import get_user_context
from mutint_experiment import models
from mutint_experiment.ancestor import ancestral_mutation_ids, ancestral_shown
from mutint_filter.view_filter import get_view_filter
from mutint_sample.mutation_matrix import RowSet, build_matrix
from mutint_sample.util import get_all_calls_filtered, get_ordered_sample_dict

from mutint_compare import analysis

logger = logging.getLogger(__name__)


def mutation_table(request):
    logger.info("mutation usage", extra=user_extra(request))
    context = get_user_context(request.user)
    try:
        start_time = time.time()
        experiment = mutint_sample.views.common.get_experiment(request)
        population = mutint_sample.views.common.get_population(request)
        sample_type = mutint_sample.views.common.get_sample_type(request)

        sample_dict = get_ordered_sample_dict(experiment.id, population, sample_type)
        # The reader's own filter, from their session. No filter_type: every mutation type
        # renders here, AMP included -- this is the one page that shows the whole experiment.
        view_filter = get_view_filter(request, experiment.id)
        calls = get_all_calls_filtered(experiment.id, view_filter=view_filter)
        # The two row sets, over the evolved calls: filtered, ancestor subtracted, AMP
        # included. The matrix annotates and offers; the reader chooses in the browser.
        thresholds = analysis.get_thresholds(request, experiment.id)
        sets = (
            RowSet("convergent", "Convergent",
                   frozenset(analysis.convergent_ids(calls, sample_dict,
                                                     at_least=thresholds.convergent))),
            RowSet("fixed", "Fixed",
                   frozenset(analysis.fixed_ids(calls, sample_dict,
                                                at_least=thresholds.fixed))),
        )
        # The rows are the same calls, unless the reader asked to see the ancestor's
        # mutations too: then they come from the raw queryset and are tinted. The sets above
        # were decided without them either way, so an ancestral row is in neither and the
        # Show menu drops it. The ancestor itself has no column: `sample_dict` left it out.
        shown = ancestral_shown(request, experiment.id)
        if shown:
            rows_from = get_all_calls_filtered(experiment.id, view_filter=view_filter,
                                               include_ancestral=True)
            ancestral_ids = ancestral_mutation_ids(experiment.id)
        else:
            rows_from, ancestral_ids = calls, frozenset()
        matrix = build_matrix(rows_from, sample_dict, experiment=experiment, sets=sets,
                              ancestral_mutation_ids=ancestral_ids,
                              csv_title="%s_ExpID%d" % (experiment.name, experiment.id))
        populations = analysis.population_count(sample_dict)

        context.update({
            "population_names": mutint_sample.views.common.get_population_names(experiment.id),
            "experiment_name": experiment.name,
            "population": population,
            "sample_type": sample_type,
            "experiment_id": experiment.id,
            "project_name": experiment.project.name,
            "project_id": experiment.project.id,
            "title": experiment.name + " Mutations",
            "template_header": "Compare",
            "matrix": matrix,
            "empty_message": "No mutations to show for these samples and this filter.",
            "thresholds": thresholds,
            "population_count": populations,
            "convergent_needed": thresholds.convergent.needed(populations),
            "fixed_needed": thresholds.fixed.needed(populations),
            "param_convergent": analysis.PARAM_CONVERGENT,
            "param_fixed": analysis.PARAM_FIXED,
            # This view honours the toggle, so the summary line may offer it.
            "ancestral_mode": "toggle",
            "ancestral_shown": shown,
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
