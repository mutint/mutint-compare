"""The cross-sample mutation table: the experiment's mutations down, its samples across.

The page is core's **mutation matrix** -- `mutint_sample.mutation_matrix.build_matrix` and
`mutation_matrix/page.html` -- with this experiment's evolved calls as its rows. What is
Compare's own is the ~30 lines below that choose the queryset: every call the experiment
holds, through the reader's filter, every mutation type included. mutint-fixation and
mutint-converge are the same page over a narrower queryset.
"""

import logging
import time

from django.http import HttpResponse
from django.template import loader

import mutint_sample.views.common
from mutint_common.logger import join_extras, user_extra
from mutint_common.util import get_user_context
from mutint_experiment import models
from mutint_filter.view_filter import get_view_filter
from mutint_sample.mutation_matrix import build_matrix
from mutint_sample.util import get_all_calls_filtered, get_reseq_ordered_dict

logger = logging.getLogger(__name__)


def mutation_table(request):
    logger.info("mutation usage", extra=user_extra(request))
    context = get_user_context(request.user)
    try:
        start_time = time.time()
        experiment = mutint_sample.views.common.get_experiment(request)
        population = mutint_sample.views.common.get_population(request)
        sample_type = mutint_sample.views.common.get_sample_type(request)

        reseq_dict = get_reseq_ordered_dict(experiment.id, population, sample_type)
        # The reader's own filter, from their session. No filter_type: every mutation type
        # renders here, AMP included -- this is the one page that shows the whole experiment.
        calls = get_all_calls_filtered(experiment.id,
                                       view_filter=get_view_filter(request, experiment.id))
        matrix = build_matrix(calls, reseq_dict, experiment=experiment,
                              csv_title="%s_ExpID%d" % (experiment.name, experiment.id))

        context.update({
            "ales": mutint_sample.views.common.get_population_names(experiment.id),
            "experiment_name": experiment.name,
            "population": population,
            "sample_type": sample_type,
            "experiment_id": experiment.id,
            "ale_project_name": experiment.project.name,
            "ale_project_id": experiment.project.id,
            "title": experiment.name + " Mutations",
            "template_header": "Compare",
            "matrix": matrix,
            "empty_message": "No mutations to show for these samples and this filter.",
        })
        logger.info("mutation performance", extra=join_extras(
            user_extra(request), {"time taken": time.time() - start_time}))
        return HttpResponse(loader.get_template("mutation_matrix/page.html").render(context, request),
                            content_type="text/html")
    except models.Experiment.DoesNotExist:
        return mutint_sample.views.common.no_experiment_selected(
            request, context, logger, "mutation table")
    except Exception as e:
        logger.exception("mutations broke", extra=user_extra(request))
        template = loader.get_template("500.html")
        context['err_message'] = str(e)
        return HttpResponse(template.render(context, request), content_type="text/html")
