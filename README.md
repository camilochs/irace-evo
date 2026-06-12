# irace-evo: Automatic Algorithm Configuration Extended with LLM-Based Code Evolution

**irace-evo** extends [irace](https://github.com/MLopez-Ibanez/irace) — the
iterated-racing tool for automatic algorithm configuration — so that it
explores the **parameter space and the code space simultaneously**: at each
iteration, a large language model proposes code variants of a user-designated
function of the algorithm under tuning, and the variants race against the
original under irace's standard statistical machinery.

Companion code for the paper:

> Chacón Sartori, C., Blum, C.:
> *irace-evo: Automatic Algorithm Configuration Extended With LLM-Based Code
> Evolution.* arXiv:2511.14794 (2025).
> https://doi.org/10.48550/arXiv.2511.14794

## How it works

- **Drop-in irace integration.** irace-evo is invoked from the standard irace
  configuration file:

  ```
  ## Code Evolution Configuration
  codeEvolution         = "TRUE"
  codeEvolutionConfig   = "./code-evolution.json"
  codeEvolutionVariants = 5
  ```

  With `codeEvolution = "FALSE"` (or absent) you get stock irace behavior.

- **`code-evolution.json`** describes the source code of the algorithm to be
  tuned, the optimization problem, and the single function the LLM is allowed
  to modify. A complete template ships in
  [`inst/templates/code-evolution.json`](inst/templates/code-evolution.json).

- **Always-From-Original (AFO).** Every new variant is generated from the
  original function, never from earlier evolved versions; previously generated
  variants enter the prompt only as diversity constraints. This keeps code
  evolution controlled and avoids drift.

- **Progressive context management.** The full source file is sent only at the
  first iteration; later iterations send selective fragments, substantially
  reducing token consumption.

- **Plugin-based language support.** Language handlers for **C++**, **Python**
  and **Java** (`inst/python/language_handlers.py`), extensible to other
  languages via a small abstract interface.

- **Compile-validated variants.** Generated variants are compiled/checked
  before entering the race; only variants that build participate.

- **Cheap by design.** The paper's experiments use lightweight models (e.g.,
  Claude Haiku 3.5) with a total usage cost under €2 per full run.

## Installation

Requires R (≥ 4.0), Python ≥ 3.9 with `openai` and/or `anthropic` packages,
and the R packages `reticulate` and `jsonlite`.

```bash
# from the repository root
./install-irace.sh          # builds and installs the R package
pip install openai anthropic
```

Set the API key of your provider as usual:

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY
# optional: pin the Python interpreter used by reticulate
export RETICULATE_PYTHON=$(which python3)
```

## Quickstart

A complete, runnable end-to-end example (a GA for the TSP whose local-search
heuristic is evolved) lives in
[`examples/tsp-ga-evolution/`](examples/tsp-ga-evolution/), including its
`code-evolution.json`. SLURM execution is supported
(`inst/templates/*slurm*`).

> **Note on the paper's case study.** The experiments reported in the paper
> apply irace-evo to a CMSA implementation for the Variable-Sized Bin Packing
> Problem; that C++ codebase is third-party and is not redistributed here.
> The included TSP-GA example exercises the identical pipeline end to end.

## Relationship to irace (license and attribution)

irace-evo is a fork of, and remains, the R package *irace* by Manuel
López-Ibáñez, Jérémie Dubois-Lacoste, Leslie Pérez Cáceres, Thomas Stützle,
Mauro Birattari and contributors, distributed under **GPL (≥ 2)**. This fork
preserves all upstream copyright notices and licensing; the code-evolution
extension (see `NEWS.md` for the precise list of changes) is © 2025–2026
Camilo Chacón Sartori and Christian Blum, released under the same license.
For the upstream tool and its documentation, see the
[irace repository](https://github.com/MLopez-Ibanez/irace) and the
[irace package page](https://mlopez-ibanez.github.io/irace/).

## Citation

```bibtex
@misc{chaconsartori2025iraceevo,
  title         = {irace-evo: Automatic Algorithm Configuration Extended
                   With LLM-Based Code Evolution},
  author        = {Chac{\'o}n Sartori, Camilo and Blum, Christian},
  year          = {2025},
  eprint        = {2511.14794},
  archivePrefix = {arXiv},
  doi           = {10.48550/arXiv.2511.14794}
}
```
