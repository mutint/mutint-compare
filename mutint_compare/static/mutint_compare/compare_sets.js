/* Compare's two row sets, Convergent and Fixed, decided in the browser.
 *
 * A line-for-line port of `mutint_compare/analysis.py`, which stays the reference: its
 * docstring has the rules and why, and `tests/test_sets_js.py` runs this file under node
 * against it over the example datasets and random cases. Change a rule there and here
 * together.
 *
 * The matrix (core's mutation_matrix.js) asks each set what it holds on every change, over
 * what the reader is showing: `state.samples` are the shown sample columns, `state.rows` the
 * rows a set may hold -- the reader's filter applied, the ancestor's left out -- with `cells`
 * indexed by sample, null where the sample does not carry the mutation or the frequency range
 * dropped it. `params` are the page's threshold boxes. So hiding a population changes what
 * converged, at once, and "at least N populations" counts the populations shown.
 */
(function (root) {
    "use strict";

    var DEFAULTS = { convergent: "2", fixed: "1" };
    //: What the importer writes into `Mutation.gene` for a mutation it could not annotate.
    var NO_GENE = "None";
    var INTEGER = /^[+-]?\d+$/;
    var DECIMAL = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/;

    /* `"2"` -> {count: 2}; `"50%"` -> {fraction: 0.5}; anything else, 0 and 0% included,
       throws -- `Threshold.parse`. */
    function parseThreshold(text) {
        text = (text || "").trim();
        if (text.charAt(text.length - 1) === "%") {
            var number = text.slice(0, -1).trim();
            if (!DECIMAL.test(number)) { throw new Error(text); }
            var value = parseFloat(number);
            if (!(value > 0 && value <= 100)) { throw new Error(text); }
            return { fraction: value / 100, text: text };
        }
        if (!INTEGER.test(text)) { throw new Error(text); }
        var count = parseInt(text, 10);
        if (count < 1) { throw new Error(text); }
        return { count: count, text: text };
    }

    /* `Threshold.needed`: a count as it stands, a fraction rounded up and never below one,
       with a hair of tolerance so 3 * (1/3) asks for 1, not 2. */
    function needed(threshold, populationCount) {
        if (threshold.count !== undefined) { return threshold.count; }
        return Math.max(1, Math.ceil(threshold.fraction * populationCount - 1e-9));
    }

    /* `analysis.gene_names`: blanks and the no-gene marker are no gene. */
    function geneNames(genes) {
        return (genes || []).filter(function (name) { return name && name !== NO_GENE; });
    }

    function populationCount(samples) {
        var seen = {};
        samples.forEach(function (s) { seen[s.population] = true; });
        return Object.keys(seen).length;
    }

    /* `convergent_ids`: the rows whose gene(s) were hit in at least `needed` populations --
       the gene converges, not the mutation, so two mutations in one gene in two lineages
       both count, and one gene hit twice in one lineage is recurrence. */
    function convergentIds(state, threshold) {
        var genesToPopulations = {}, mutationGenes = [];
        state.rows.forEach(function (row) {
            var populations = {};
            state.samples.forEach(function (s) {
                if (row.cells[s.index]) { populations[s.population] = true; }
            });
            var hit = Object.keys(populations);
            if (!hit.length) { return; }
            var names = geneNames(row.genes);
            mutationGenes.push([row.id, names]);
            names.forEach(function (name) {
                var set = genesToPopulations[name] = genesToPopulations[name] || {};
                hit.forEach(function (p) { set[p] = true; });
            });
        });
        var need = needed(threshold, populationCount(state.samples));
        return mutationGenes.filter(function (pair) {
            return pair[1].some(function (name) {
                return Object.keys(genesToPopulations[name]).length >= need;
            });
        }).map(function (pair) { return pair[0]; });
    }

    /* `fixed_ids`: the rows present at both of the last two time points sampled from at least
       `needed` populations -- the time points from the samples, not the calls. */
    function fixedIds(state, threshold) {
        var timePoints = {};
        state.samples.forEach(function (s) {
            if (s.time === null || s.time === undefined) { return; }
            (timePoints[s.population] = timePoints[s.population] || {})[s.time] = true;
        });
        var fixedIn = {};
        Object.keys(timePoints).forEach(function (population) {
            var sampled = Object.keys(timePoints[population]).map(Number).sort(function (a, b) { return a - b; });
            if (sampled.length < 2) { return; }
            var lastTwo = sampled.slice(-2);
            var at = function (time) {
                var present = {};
                state.samples.forEach(function (s) {
                    if (s.population !== population || s.time !== time) { return; }
                    state.rows.forEach(function (row) { if (row.cells[s.index]) { present[row.id] = true; } });
                });
                return present;
            };
            var last = at(lastTwo[1]), secondLast = at(lastTwo[0]);
            Object.keys(last).forEach(function (id) {
                if (secondLast[id]) { fixedIn[id] = (fixedIn[id] || 0) + 1; }
            });
        });
        var need = needed(threshold, populationCount(state.samples));
        return Object.keys(fixedIn).filter(function (id) { return fixedIn[id] >= need; }).map(Number);
    }

    /* A box's threshold, or the default with a sentence saying so -- `_parse_or`'s posture:
       a threshold that silently does nothing is worse than one that visibly went back. */
    function thresholdFrom(params, name, label) {
        var text = params && typeof params[name] === "string" ? params[name] : DEFAULTS[name];
        if (!text.trim()) { return { threshold: parseThreshold(DEFAULTS[name]) }; }
        try {
            return { threshold: parseThreshold(text) };
        } catch (bad) {
            return {
                threshold: parseThreshold(DEFAULTS[name]),
                error: "“" + text + "” is not a number of populations or a percentage; " +
                       label + " is using " + DEFAULTS[name] + "."
            };
        }
    }

    function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

    function convergentSet(state, params) {
        var got = thresholdFrom(params, "convergent", "Convergent");
        var populations = populationCount(state.samples);
        return {
            ids: convergentIds(state, got.threshold),
            note: "Convergent: a gene hit in at least " + needed(got.threshold, populations) +
                  " of the " + plural(populations, "population") + " shown (" + got.threshold.text +
                  "), counting lineages rather than samples.",
            error: got.error
        };
    }

    function fixedSet(state, params) {
        var got = thresholdFrom(params, "fixed", "Fixed");
        var populations = populationCount(state.samples);
        return {
            ids: fixedIds(state, got.threshold),
            note: "Fixed: present at both of the last two time points shown from a population, " +
                  "in at least " + needed(got.threshold, populations) + " of the " +
                  plural(populations, "population") + " shown (" + got.threshold.text + ").",
            error: got.error
        };
    }

    var api = {
        DEFAULTS: DEFAULTS, parseThreshold: parseThreshold, needed: needed,
        convergentIds: convergentIds, fixedIds: fixedIds,
        convergent: convergentSet, fixed: fixedSet
    };
    if (typeof module !== "undefined" && module.exports) { module.exports = api; }
    if (root && root.document) {
        // The matrix's registry, whichever script got here first (mutation_matrix.js says).
        root.mutintMatrixSets = root.mutintMatrixSets || (function () {
            var registered = {};
            return {
                register: function (key, fn) { registered[key] = fn; },
                get: function (key) { return registered[key]; }
            };
        }());
        root.mutintMatrixSets.register("convergent", convergentSet);
        root.mutintMatrixSets.register("fixed", fixedSet);
    }
}(typeof window !== "undefined" ? window : this));
