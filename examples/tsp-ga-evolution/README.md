# Example: evolving one function of a BRKGA

The program in `src/brkga.cpp` is a biased random-key genetic algorithm (BRKGA)
for the Longest Run Subsequence (LRS) problem: given a string, pick a
subsequence made of runs of equal letters, as long as possible, using each
letter in at most one run. irace tunes four parameters of the BRKGA, and
irace-evo lets an LLM rewrite one function, `order_chromosome()`, which turns
a chromosome of random keys into the order the decoder reads it in.

(The folder is called `tsp-ga-evolution` for historical reasons. There is no
TSP in it.)

## Files

| File | What it is |
|---|---|
| `src/brkga.cpp` | the algorithm; `order_chromosome()` is the function the LLM may change |
| `parameters.txt` | the four parameters irace tunes: `-p`, `-pe`, `-pm`, `-rhoe` |
| `scenario.txt` | the irace scenario, with the three `codeEvolution` lines |
| `code-evolution.json` | the problem in words, the function, the build, the model, the validation test |
| `target-runner` | runs one configuration on one instance and prints its cost |
| `tuning_instances/`, `instances-list.txt` | the six instances irace tunes on |
| `instances/` | 1050 more instances (lengths 100 to 5000, alphabets of 2 to 32 letters) |

## Run it

From this folder, after installing irace-evo (see the main README):

```bash
export ANTHROPIC_API_KEY=...          # or set api_provider to openai and export OPENAI_API_KEY
irace --scenario scenario.txt
```

Each algorithm run takes `TIME_LIMIT` seconds (120 by default), so the full
scenario (180 runs, 10 in parallel) takes about 40 minutes. For a first look,
`TIME_LIMIT=5 irace --scenario scenario.txt` takes a few minutes.

To try the whole pipeline without an API key, `tests/evo/run-example.sh` (in
the repository root) runs this example against a stand-in for the LLM.

## What appears in the folder

| Path | Contents |
|---|---|
| `bin/brkga` | the original program, compiled on the first run |
| `bin/algorithm_var_*_iter<k>` | the variants of iteration k |
| `irace-evo-sources/variant_<i>_iter<k>.cpp` | the full source of each variant |
| `irace-evo-llm-logs/` | what each variant is, and the Python side of each iteration |
| `logs/irace-evo-llm.log` | every prompt and every answer |
| `.irace_evo_variants.csv` | which configuration runs which program |
| `irace.Rdata` | irace's log, as usual |

A new run in the same folder first deletes the variants, sources and
`irace-evo-llm-logs/` of the previous one. `make clean` deletes all of the
above except the instances.

## Things to know about this program

- It maximises: it prints the length of the subsequence it found. The target
  runner returns the negative, since irace minimises. Set `MAXIMIZE=0` for a
  program that prints a cost.
- It seeds its random numbers from the clock and ignores irace's seed, so two
  runs of the same configuration differ.
- `target-runner-slurm` is the runner used on a SLURM cluster; its path to
  the program is that cluster's and must be edited.
