"""The cross-sample mutation table.

Moved out of aledb-core's `aledb_seq/views/mutations.py` unchanged. What stayed behind is
everything this is built from and everything it shares: `mutation_table_builder`, which
Search, Export, aledb-fixation and aledb-converge all call; `base_table_template.html` and
`table_template.js`, which three other pages render; and the tag and filter endpoints those
pages POST to. This module is the ~85 lines that were only ever Compare's.
"""

import json
import logging
import time

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.template import loader
from django.utils.safestring import mark_safe

import aledb_common.constants
import aledb_seq.views.common
from aledb_common.constants import REFSEQ_COLUMN_IN_MUT_TABLE
from aledb_common.logger import join_extras, user_extra
from aledb_common.util import get_user_context
from aledb_experiment import models
from aledb_seq.util import get_all_observed_mutations_filtered, get_reseq_ordered_dict
from aledb_seq.views import mutation_table_builder

logger = logging.getLogger(__name__)


def mutation_table(request):
    logger.info("mutation usage", extra=user_extra(request))
    context = get_user_context(request.user)
    try:
        start_time = time.time()
        experiment = aledb_seq.views.common.get_ale_experiment(request)

        exp_name = experiment.name
        ale_no = aledb_seq.views.common.get_ale_id(request)
        sample_type = aledb_seq.views.common.get_sample_type(request)
        aleid_ale_id_list = aledb_seq.views.common.get_aleid_ale_id_list(experiment.ale_id, True)

        ordered_reseq_dict = get_reseq_ordered_dict(experiment.ale_id, ale_no, sample_type, request)

        table_header = mutation_table_builder.get_table_header(request.user, ordered_reseq_dict, experiment)

        show_exp_filtered = request.GET.get('show_exp_filtered', '') == '1'

        # No filter_type: every mutation type renders here, AMP included. This used to pass
        # filter_type="AMP", which -- the value naming is inverted, it means *exclude* --
        # kept AMP rows out, and /mutations/amplifications was the only place they appeared.
        # That page is gone, so excluding them here would hide them entirely.
        table_body = _get_table_body(experiment, ordered_reseq_dict, request.user,
                                     skip_experiment_filter=show_exp_filtered)

        hidden_columns = request.GET.get('hidden_columns', "")

        template = loader.get_template("base_table_template.html")

        context.update({"ales": aleid_ale_id_list,
                        "ale_experiment_name": exp_name,
                        "ale_no": ale_no,
                        "sample_type": sample_type,
                        "ale_experiment_id": experiment.ale_id,
                        "ale_project_name": experiment.project.name,
                        "ale_project_id": experiment.project.id,
                        "table_body": mark_safe(json.dumps(table_body, cls=DjangoJSONEncoder)),
                        "title": exp_name + " Mutations",
                        "table_header": table_header,
                        "template_header": "Compare",
                        "hidden_columns": hidden_columns,
                        "refseq_column": REFSEQ_COLUMN_IN_MUT_TABLE,
                        "tag_dropdown": aledb_common.constants.TAGS,
                        # The two "show filtered" checkboxes are Compare's alone -- no other
                        # page that renders base_table_template.html populates them. This flag
                        # is what keeps them off Fixation, Converge and Search, where they
                        # used to render permanently inert.
                        "show_filter_toggles": True,
                        "show_exp_filtered": show_exp_filtered,
                        })
        logger.info("mutation performance", extra=join_extras(user_extra(request), {"time taken": time.time() - start_time}))

        return HttpResponse(template.render(context, request), content_type="text/html")
    except models.AleExperiment.DoesNotExist:
        return aledb_seq.views.common.no_experiment_selected(
            request, context, logger, "mutation table")
    except Exception as e:
        logger.exception("mutations broke", extra=user_extra(request))
        template = loader.get_template("500.html")
        context['err_message'] = str(e)
        return HttpResponse(template.render(context, request), content_type="text/html")


def _get_table_body(experiment, ordered_reseq_dict, user, filter_type=None,
                    skip_experiment_filter=False):
    obs_mutations = get_all_observed_mutations_filtered(experiment.ale_id, filter_type,
                                                        skip_experiment_filter=skip_experiment_filter)
    return mutation_table_builder.get_mutation_table_body(user, obs_mutations, ordered_reseq_dict, experiment)
