"""Run the browser's row sets -- `static/mutint_compare/compare_sets.js` -- under node.

Compare decides Convergent and Fixed in the browser, so a test of what they hold has to run
that script. `state_from_page` builds the `state` the matrix hands it from a rendered page --
the rows JSON and the sample headers -- with every sample shown and the ancestral rows left out,
which is what the page does before the reader touches anything. `NODE` is None where node is
not installed; the tests that need it skip, saying so.
"""

import json
import os
import re
import shutil
import subprocess

NODE = shutil.which("node")
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "static", "mutint_compare", "compare_sets.js")
SKIP_REASON = "node is not installed, so the browser's row sets cannot be run here"

ROWS = re.compile(r'<script id="mutation-matrix-rows" type="application/json">(.*?)</script>', re.S)
HEADER = re.compile(r'data-sample="(\d+)" data-index="(\d+)" data-population="([^"]*)" '
                    r'data-treatment="[^"]*" data-time="([^"]*)"')

_PROGRAM = """
const api = require(process.argv[1]);
let input = "";
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
    const job = JSON.parse(input);
    const out = job.calls.map(call => {
        if (call.parse !== undefined) {
            try { const t = api.parseThreshold(call.parse); return {count: t.count === undefined ? null : t.count, fraction: t.fraction === undefined ? null : t.fraction, needed: api.needed(t, call.populations)}; }
            catch (e) { return {error: true}; }
        }
        const result = api[call.set](call.state, call.params || {});
        return {ids: result.ids.slice().sort((a, b) => a - b), note: result.note, error: result.error || null};
    });
    process.stdout.write(JSON.stringify(out));
});
"""


def run(calls):
    """Each call is `{set, state, params}` or `{parse, populations}`; answers in order."""
    completed = subprocess.run([NODE, "-e", _PROGRAM, SCRIPT], input=json.dumps({"calls": calls}),
                               capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def ids(set_key, state, params=None):
    return set(run([{"set": set_key, "state": state, "params": params or {}}])[0]["ids"])


def state_from_page(html):
    rows = json.loads(ROWS.search(html).group(1))
    samples = [{"index": int(index), "population": population,
                "time": float(time) if time else None}
               for _sample, index, population, time in HEADER.findall(html)]
    return {"samples": samples,
            "rows": [{"id": row["id"], "genes": row.get("genes", []), "cells": row["samples"]}
                     for row in rows if not row.get("ancestral")]}, rows
