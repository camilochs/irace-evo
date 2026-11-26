# irace-evo

You have an algorithm that already works, and irace has tuned its parameters.
What still holds it back is one function: the rule that scores a move, orders
the candidates or picks the next component. No parameter value fixes that
rule; it has to be written differently. irace-evo asks an LLM to write
variants of that one function and races them inside irace, so the parameters
and the code are tuned together.

It is [irace](https://github.com/MLopez-Ibanez/irace) with one addition: a
configuration is a pair (θ, A), parameter values θ and a version A of the
function. You turn it on with three lines in the scenario:

```
codeEvolution         = "TRUE"
codeEvolutionConfig   = "./code-evolution.json"
codeEvolutionVariants = 5
```

Without them it is irace.

Christian Blum and I describe the method in the paper
[irace-evo: Automatic Algorithm Configuration Extended With LLM-Based Code Evolution](https://doi.org/10.48550/arXiv.2511.14794)
(MIC 2026). There it improves the state-of-the-art CMSA for the
Variable-Sized Bin Packing Problem at a cost of €1.57 for ten runs with
Claude Haiku 3.5. That CMSA code belongs to its authors and is not in this
repository; the example here is a smaller one you can run in minutes.

## What happens in each iteration

1. irace samples new parameter values, as usual.
2. The LLM writes `codeEvolutionVariants` versions of the function. Each is
   written from the original code, never from an earlier variant; the
   variants already written in the iteration go into the prompt so the next
   one differs from them. The first iteration sends the whole source file,
   later ones only the function and the parts of the file it needs.
3. Each version is compiled (a compiler error goes back to the LLM a couple
   of times) and run once on a test instance. The ones that fail are dropped.
4. Every new configuration is paired with one version: one of this
   iteration's, one that an elite configuration already uses, or the
   original. A configuration keeps its version for the rest of the run.
5. irace races the pairs and keeps the elites, as usual.

From iteration `evolution_focus_iteration` on (3 unless you change it), the
prompt asks for broader structural changes instead of moderate ones.

## Install

You need R 4.0 or later, Python 3.9 or later and a C++ compiler. On Linux,
also Python's shared library (R loads Python through it) and the libraries
two R packages compile against, since R builds them from source there; on
Debian or Ubuntu:

```bash
sudo apt-get install python3-dev python3-venv g++ make libuv1-dev libpng-dev zlib1g-dev
```

Give the LLM side its own Python environment, and tell R to use it:

```bash
python3 -m venv ~/.venvs/irace-evo
export RETICULATE_PYTHON=~/.venvs/irace-evo/bin/python
```

Then, from the root of this repository:

```bash
./install-irace.sh
```

It installs the R packages irace needs, irace-evo itself, and the two Python
packages the LLM side imports (`openai` and `anthropic`) into that
environment, and prints where the `irace` command is. The R package is still
called `irace`, so it replaces an irace you had installed. Keep
`RETICULATE_PYTHON` set (in your shell profile, say) when you run irace.

The last lines it prints, on a fresh Ubuntu 24.04 machine with R 4.4:

```
Installed. The irace command is /usr/local/lib/R/site-library/irace/bin/irace; to call it as 'irace':
  export PATH="/usr/local/lib/R/site-library/irace/bin:$PATH"
```

## Try it without an API key

`tests/evo/run-example.sh` runs the example below end to end against a small
local server that answers like the OpenAI or the Anthropic API. It returns
the function it was given with a comment added, so nothing improves, but
every step runs: prompts, compilation, validation, pairing and racing. Then
`tests/evo/check_run.py` reads what happened and checks it against the
method:

```bash
tests/evo/run-example.sh anthropic /tmp/evo-run
python3 tests/evo/check_run.py /tmp/evo-run --temperature 1.0 --top-p 0.9
```

It takes about four minutes and prints:

```
PASS each configuration keeps its code :: 52 configurations, 0 ran more than one program
PASS the fake LLM was asked for variants :: 8 requests, 8 variant requests, iterations [1, 2, 3, 4]
PASS every variant starts from the original code (AFO) :: 0 of 8 prompts start from an earlier variant
PASS whole file in iteration 1, fragments after (R_i) :: 0 of 8 prompts with the wrong context
PASS standard focus before iteration 3, aggressive from it (E_i) :: 0 of 8 prompts with the wrong focus
PASS the configured temperature and top_p are sent (Phi) :: wanted (1.0, 0.9), sent {(1, 0.9): 8}
PASS the API key is not written to any log :: not found
PASS only the configured provider is called :: request paths {'/v1/messages': 8}
```

The irace output (`/tmp/evo-run/irace.out`) shows the pairing in each iteration:

```
# 2026-11-26 01:47:10 UTC: irace-evo: 16 new configurations paired with 3 code variants (2 new, 0 from the elites, and the original)
# 2026-11-26 01:48:04 UTC: irace-evo: 13 new configurations paired with 4 code variants (2 new, 2 from the elites, and the original)
# 2026-11-26 01:49:00 UTC: irace-evo: 12 new configurations paired with 5 code variants (2 new, 3 from the elites, and the original)
# 2026-11-26 01:49:56 UTC: irace-evo: 11 new configurations paired with 5 code variants (2 new, 3 from the elites, and the original)
```

and, at the end, the best configurations with the version each one runs (the
winning function and the LLM usage follow, here with the stand-in's
functions):

```
# Best configurations as commandlines (first number is the configuration ID, second is the variant; listed from best to worst according to the sum of ranks):
36 variant_1_iter3 -p 178 -pe 0.1912 -pm 0.1313 -rhoe 0.6374
45 variant_1_iter1 -p 230 -pe 0.1716 -pm 0.2376 -rhoe 0.6436
44 original        -p 145 -pe 0.2059 -pm 0.1087 -rhoe 0.64
19 original        -p 184 -pe 0.2001 -pm 0.1138 -rhoe 0.6345
```

## Run the example with a real model

`examples/tsp-ga-evolution/` is a BRKGA for the Longest Run Subsequence
problem in C++; the LLM may rewrite `order_chromosome()`. Its
[README](examples/tsp-ga-evolution/README.md) explains the files.

```bash
cd examples/tsp-ga-evolution
export ANTHROPIC_API_KEY=...
TIME_LIMIT=5 irace --scenario scenario.txt
```

`TIME_LIMIT` is the time of each algorithm run in seconds; 5 gives a run of
a few minutes, the default of 120 about forty. At the end irace prints the
same blocks as the run without an API key above, with the functions your
model wrote.

## Use it on your own algorithm

1. Put your source file and its build where irace runs (`execDir`), with
   the original program compiled to `bin/<source file name without
   extension>`.
2. Copy [`inst/templates/code-evolution.json`](inst/templates/code-evolution.json)
   and fill it in: the problem in words (`problem_context`), the file and
   the one function the LLM may change, how to compile, which model, and
   the command that tests a variant. The comments in the template explain
   each option.
3. Write a target runner that reads `.irace_evo_variants.csv`
   (`config_id,executable_path,variant_id`) and runs the program paired with
   its configuration. [`inst/templates/target-runner-evolution.tmpl`](inst/templates/target-runner-evolution.tmpl)
   does that; adapt the line that builds the command. The example's
   `target-runner` also runs the original for configurations of plain irace.
4. Add the three `codeEvolution` lines to your scenario and run irace.

The function works best when it is small and does one thing: a scoring rule,
a comparison, an ordering. A function that mixes several parts of the
algorithm gives the LLM more ways to break it.

## What to expect

- Only one function changes. Numbers the LLM writes inside it (weights,
  thresholds) are not tuned by irace.
- The cost shown at the end is an estimate from token counts; your
  provider's bill is the real one.
- Some models refuse `temperature` and `top_p`. irace-evo then calls them
  without these values and says so once.
- C++ is what the paper and the example use. The Python and Java handlers
  have no end-to-end test yet, and SLURM support has not been tested on a
  cluster since the changes listed in `NEWS.md`.
- A run deletes what the previous run left in the same folder (variants,
  their sources and the LLM logs).

## Relationship to irace

irace-evo is a fork of the R package irace by Manuel López-Ibáñez, Jérémie
Dubois-Lacoste, Leslie Pérez Cáceres, Thomas Stützle, Mauro Birattari and
contributors, under GPL (≥ 2). All upstream notices are kept; the code
evolution (see `NEWS.md` for every change) is © 2025–2026 Camilo Chacón
Sartori and Christian Blum, under the same license. For irace itself, see
[its repository](https://github.com/MLopez-Ibanez/irace) and the upstream
README, kept here as [`README-irace.md`](README-irace.md).

## Citation

```bibtex
@misc{chaconsartori2025iraceevo,
  title         = {irace-evo: Automatic Algorithm Configuration Extended
                   With LLM-Based Code Evolution},
  author        = {Chac{\'o}n Sartori, Camilo and Blum, Christian},
  year          = {2025},
  eprint        = {2511.14794},
  archivePrefix = {arXiv},
  doi           = {10.48550/arXiv.2511.14794},
  note          = {To appear in MIC 2026, LNCS 16914}
}
```
