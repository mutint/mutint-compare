# mutint-compare

The cross-sample mutation table for [MutInt](https://github.com/mutint/mutint-core): mutations
down, samples across, at `/compare/`.

It renders mutint-core's **mutation matrix** (`mutint_sample.mutation_matrix.build_matrix`) over
an experiment's evolved calls, through the reader's filter, with every mutation type included. A
**Show** menu offers two derived row sets, each with its rule's threshold exposed:

- **Convergent** — mutations hitting a gene in at least *N* populations, or at least *X%* of the
  populations shown.
- **Fixed** — mutations present at both of the last two sampled time points of a population.

Those were once two separate plugins (`mutint-converge`, `mutint-fixation`); folding them into
one menu is why core grew the generic row-set mechanism they now use.

## Installing

Add it as a submodule of an assembled project and it registers itself — no edits to
`config/settings.py` or `config/urls.py`:

```bash
git submodule add ../mutint-compare mutint-compare
```

MIT licensed. See [mutint-core](https://github.com/mutint/mutint-core) for the platform.
