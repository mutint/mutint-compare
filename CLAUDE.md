# CLAUDE.md — mutint-compare

The cross-sample mutation table: mutations down, samples across, at `/compare/`. It is core's
**mutation matrix** (`mutint_sample.mutation_matrix.build_matrix`, `mutation_matrix/page.html`)
over the experiment's evolved calls through the reader's filter, every mutation type included.
The suite-level `CLAUDE.md` and `mutint-core/CLAUDE.md` (**Compare is a plugin**, **The
mutation matrix**) carry the design of the matrix itself; this file is what is Compare's own.

## Convergent and Fixed are row sets, and used to be plugins

`mutint-converge` and `mutint-fixation` were each this page over a narrower queryset with one
hard-coded rule, an export type, an example dataset and a nav entry. They are `analysis.py`
now: two functions returning mutation ids, handed to `build_matrix(sets=...)` as `RowSet`s,
which the matrix annotates rows with and offers in its **Show** menu. Nothing in core knows
what "convergent" means; the seam is generic and this plugin is its only producer.

The rules at their defaults are the old ones exactly. What is new is the **threshold**: at
least *N* populations, or at least *X%* of the populations shown, rounded up. `Threshold.parse`
accepts `2` or `50%`; `get_thresholds` reads `convergent_min` and `fixed_min` from the query
string when present and remembers them in the session per experiment, the way
`get_view_filter` does and for the same reason -- the sidebar's link carries no parameters.

Three things the fold changed, deliberately:

- **AMP is in the sets.** The old pages passed `filter_type='AMP'` (exclude); Compare shows
  every type, and the sets are computed over the same calls the rows are. A reader who does
  not want AMP hides it with the Types menu, and the count in the Show menu follows.
- **The time axis comes from the samples, not the calls.** A time point every call was
  filtered out of is still the last time point, and nothing fixed there. The old
  implementation compared the last two time points *with calls*.
- **The export types `fixed_mut` and `converged_mut` are gone.** Export is the matrix's own
  CSV menu: the rows showing, or all of them.

`compare/page.html` extends core's page through its two blocks, `matrix_form_fields` for the
two inputs and `matrix_summary` for the sentence saying what the thresholds resolved to.

## Ancestral rows are display, not data

The designated ancestor's mutations are subtracted from the calls both sets are decided on,
and hidden from the table by default. `ancestral_shown` -- core's toggle, one choice per
experiment in the session, shared with the per-sample page, offered by the button in the
summary line because the view sets `ancestral_mode = "toggle"` -- makes the view build its
*rows* from `get_all_calls_filtered(include_ancestral=True)` and hand `build_matrix` the ids
to tint. The sets are still computed first, from the evolved calls, so an ancestral row is in
neither and Convergent or Fixed in the Show menu drops it; "All" and the CSV export count it,
because it is a row the server produced. The ancestor itself has no column:
`get_ordered_sample_dict` leaves it out either way, and its own calls fall through
`build_matrix` for want of one. `test_ancestral_display.py` pins each of those.

## Tests

`./mutint test mutint_compare` from an assembled project; core has no plugin discovery. To run
uncommitted root-checkout edits, put the root checkouts on `PYTHONPATH` ahead of the
submodule clones. `test_example_sets.py` asserts the two example datasets' known answers
through the page, reading the rows JSON the matrix hands the browser.
