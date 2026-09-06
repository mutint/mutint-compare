"""What counts as convergent and as fixed, over the calls Compare already holds.

These were two plugins, mutint-converge and mutint-fixation, each the mutation matrix over a
narrower queryset with one hard-coded rule. They are two **row sets** on Compare now -- the
Show menu -- and the rules have a knob each: how many populations, or what fraction of them,
a mutation has to reach.

**Convergent**: a mutation converges when any gene it touches was hit in at least *N*
populations (ALEs). It is the *gene* that converges, not the mutation, so two different
mutations in one gene in two lineages both qualify; the same gene hit twice in one lineage is
recurrence, not convergence. The default *N* is 2, which is the old rule exactly.

**Fixed**: a mutation is fixed *in a population* when it is present at both of the last two
time points sampled from it -- the last two *sampled*, so an ALE sampled at 1, 500 and 30000
compares 500 with 30000, and one sampled once can never fix anything. The row qualifies when
that holds in at least *N* populations; the default is 1, the old rule.

Both read the list of calls the page's rows are built from, so what the reader's filter and
the ancestor subtraction removed upstream is gone here too -- which is the only place the
filter can go. Fixation asks what is present at the last time point, so hiding a
low-frequency call there changes the answer, and filtering the result afterwards would show
one set of rows for a different claim. The old modules said the same thing.

Populations and time points come from the samples the page selected (`sample_dict`), not from
the calls: a time point every call was filtered out of is still the last time point, and
nothing fixed there.
"""

import collections
import math
from dataclasses import dataclass
from typing import Optional

from mutint_common.util import get_gene_list

#: Query-string parameters, and what they mean when absent.
PARAM_CONVERGENT = "convergent_min"
PARAM_FIXED = "fixed_min"
SESSION_KEY = "mutint_compare_thresholds"
MAX_REMEMBERED_EXPERIMENTS = 20


@dataclass(frozen=True)
class Threshold:
    """At least `count` populations, or at least `fraction` of them, rounded up.

    Written as the reader types it: `2`, or `50%`. `needed(n)` resolves it against the
    number of populations on the page, and a fraction always asks for at least one.
    """
    count: Optional[int] = None
    fraction: Optional[float] = None

    @classmethod
    def parse(cls, text):
        """`"2"` -> count 2; `"50%"` -> fraction 0.5. Raises ValueError for anything else,
        including 0 and 0%: a set nothing has to reach is All, which the menu already has."""
        text = (text or "").strip()
        if text.endswith("%"):
            value = float(text[:-1])
            if not 0 < value <= 100:
                raise ValueError(text)
            return cls(fraction=value / 100)
        value = int(text)
        if value < 1:
            raise ValueError(text)
        return cls(count=value)

    def needed(self, population_count):
        if self.count is not None:
            return self.count
        # A hair of tolerance so 3 * (1/3) asks for 1, not 2.
        return max(1, math.ceil(self.fraction * population_count - 1e-9))

    def __str__(self):
        if self.count is not None:
            return str(self.count)
        return "%g%%" % (self.fraction * 100)


DEFAULT_CONVERGENT = Threshold(count=2)
DEFAULT_FIXED = Threshold(count=1)


@dataclass(frozen=True)
class Thresholds:
    convergent: Threshold = DEFAULT_CONVERGENT
    fixed: Threshold = DEFAULT_FIXED

    def as_dict(self):
        return {"convergent": str(self.convergent), "fixed": str(self.fixed)}

    @classmethod
    def from_dict(cls, stored):
        return cls(convergent=_parse_or(stored.get("convergent"), DEFAULT_CONVERGENT),
                   fixed=_parse_or(stored.get("fixed"), DEFAULT_FIXED))


def _parse_or(text, default):
    try:
        return Threshold.parse(text)
    except (TypeError, ValueError):
        # The page re-renders showing what is in force. A threshold that silently does
        # nothing is worse than one that visibly went back to its default.
        return default


def get_thresholds(request, experiment_id):
    """The thresholds this reader set for this experiment. Never None.

    The same resolution `get_view_filter` uses, for the same reason: the parameters are read
    when **present** in the query string and remembered in the session, so the sidebar's
    links -- which carry no parameters -- bring the reader back to the page as they left it.
    What is remembered is a display preference derived from the URL they are looking at.
    """
    store = request.session.get(SESSION_KEY) or {}
    key = str(experiment_id)
    if PARAM_CONVERGENT in request.GET or PARAM_FIXED in request.GET:
        thresholds = Thresholds.from_dict({"convergent": request.GET.get(PARAM_CONVERGENT),
                                           "fixed": request.GET.get(PARAM_FIXED)})
        store.pop(key, None)
        store[key] = thresholds.as_dict()
        while len(store) > MAX_REMEMBERED_EXPERIMENTS:
            del store[next(iter(store))]
        request.session[SESSION_KEY] = store
        return thresholds
    if key in store:
        return Thresholds.from_dict(store[key])
    return Thresholds()


def population_count(sample_dict):
    return len({sample.population_id for sample in sample_dict.values()})


def convergent_ids(calls, sample_dict, *, at_least=DEFAULT_CONVERGENT):
    """The ids of the mutations whose gene(s) were hit in at least `at_least` populations."""
    population_of = {sample_id: sample.population_id for sample_id, sample in sample_dict.items()}
    genes_to_populations = collections.defaultdict(set)
    mutation_genes = {}
    for call in calls:
        if call.present is not True or call.sample_id not in population_of:
            continue
        names = mutation_genes.get(call.mutation_id)
        if names is None:
            # An intergenic mutation names two genes; an unannotated one names none, and
            # "no gene" must not be a gene every such mutation shares.
            gene = call.mutation.gene
            names = mutation_genes[call.mutation_id] = (
                [name for name in get_gene_list(gene) if name] if gene else [])
        for name in names:
            genes_to_populations[name].add(population_of[call.sample_id])
    needed = at_least.needed(population_count(sample_dict))
    return {mutation_id
            for mutation_id, names in mutation_genes.items()
            if any(len(genes_to_populations[name]) >= needed for name in names)}


def fixed_ids(calls, sample_dict, *, at_least=DEFAULT_FIXED):
    """The ids of the mutations present at both of the last two sampled time points of at
    least `at_least` populations."""
    # population -> the time points sampled from it, from the samples rather than the calls.
    time_points = collections.defaultdict(set)
    for sample in sample_dict.values():
        if sample.time_point is not None:
            time_points[sample.population_id].add(sample.time_point)
    # (population, time point) -> the mutations present there, across its samples.
    present = collections.defaultdict(set)
    for call in calls:
        sample = sample_dict.get(call.sample_id)
        if call.present is not True or sample is None or sample.time_point is None:
            continue
        present[(sample.population_id, sample.time_point)].add(call.mutation_id)

    fixed_in = collections.Counter()
    for population, sampled in time_points.items():
        if len(sampled) < 2:
            continue
        last, second_last = sorted(sampled)[-2:][::-1]
        for mutation_id in present[(population, last)] & present[(population, second_last)]:
            fixed_in[mutation_id] += 1
    needed = at_least.needed(population_count(sample_dict))
    return {mutation_id for mutation_id, count in fixed_in.items() if count >= needed}
