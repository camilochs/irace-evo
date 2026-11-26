#!/bin/bash
# Runs the example in examples/tsp-ga-evolution end to end against the fake
# LLM (tests/evo/fake_llm.py): no API key, no cost, a few minutes.
#
#   tests/evo/run-example.sh [openai|anthropic] [workdir]
#
# It copies the example to a scratch directory, starts the fake LLM, runs
# irace with a small budget and one-second algorithm runs, and leaves in the
# work directory:
#   irace.out       the irace output
#   requests.jsonl  every request the fake LLM received
#   runs.csv        config_id,executable of every algorithm run
# Then tests/evo/check_run.py reads them and checks what the paper says
# must hold. Requires R with this package installed, Python 3 with openai and
# anthropic, and g++.
set -euo pipefail
provider="${1:-openai}"
work="${2:-$(mktemp -d)}"
here="$(cd "$(dirname "$0")" && pwd)"
example="$here/../../examples/tsp-ga-evolution"

mkdir -p "$work"
cp -R "$example/src" "$example/tuning_instances" "$example/instances-list.txt" \
      "$example/parameters.txt" "$example/target-runner" "$example/code-evolution.json" "$work/"
cp "$example/scenario.txt" "$work/scenario-example.txt"
cd "$work"

# The example asks a real model; point it at the fake one.
python3 - "$provider" << 'PY'
import json, sys
c = json.load(open("code-evolution.json"))
c["llm_config"]["api_provider"] = sys.argv[1]
c["llm_config"]["model"] = "fake-model"
c["llm_config"]["api_key"] = "fake-key"
# The paper's LLM hyperparameters (Sect. 4.1), to check they are the ones sent.
c["llm_config"]["temperature"] = 1.0
c["llm_config"]["top_p"] = 0.9
json.dump(c, open("code-evolution.json", "w"), indent=2)
PY

cat > scenario.txt << 'SC'
parameterFile = "./parameters.txt"
trainInstancesDir = "./tuning_instances/"
trainInstancesFile = "instances-list.txt"
targetRunner = "./target-runner"
codeEvolution = "TRUE"
codeEvolutionConfig = "./code-evolution.json"
codeEvolutionVariants = 2
maxExperiments = 400
parallel = 4
seed = 1
SC

port=$((20000 + RANDOM % 20000))
python3 "$here/fake_llm.py" "$port" "$work/requests.jsonl" order_chromosome &
fake=$!
trap 'kill $fake 2>/dev/null || true' EXIT
sleep 1
export OPENAI_BASE_URL="http://127.0.0.1:$port/v1" ANTHROPIC_BASE_URL="http://127.0.0.1:$port"
export TIME_LIMIT=1 RUN_LOG="$work/runs.csv"
Rscript -e 'irace::irace_cmdline()' > irace.out 2>&1 || { tail -40 irace.out; exit 1; }
echo "$work"
