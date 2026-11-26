#!/bin/bash
# The Java counterpart of run-example.sh: runs tests/evo/java-example (a
# randomised greedy for the knapsack problem whose score() the LLM may
# rewrite) against the fake LLM, and leaves irace.out, requests.jsonl and
# runs.csv in the work directory for check_run.py.
#
#   tests/evo/run-java-example.sh [openai|anthropic] [workdir]
set -euo pipefail
provider="${1:-anthropic}"
work="${2:-$(mktemp -d)}"
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$work"
cp -R "$here/java-example/." "$work/"
cd "$work"
python3 - "$provider" << 'PY'
import json, sys
c = json.load(open("code-evolution.json"))
c["llm_config"].update(api_provider=sys.argv[1], model="fake-model", api_key="fake-key")
json.dump(c, open("code-evolution.json", "w"), indent=2)
PY
cat > scenario.txt << 'SC'
parameterFile = "./parameters.txt"
trainInstancesDir = "./instances/"
targetRunner = "./target-runner"
codeEvolution = "TRUE"
codeEvolutionConfig = "./code-evolution.json"
codeEvolutionVariants = 2
maxExperiments = 300
parallel = 4
seed = 1
SC
port=$((20000 + RANDOM % 20000))
python3 "$here/fake_llm.py" "$port" "$work/requests.jsonl" score java &
fake=$!
trap 'kill $fake 2>/dev/null || true' EXIT
sleep 1
export OPENAI_BASE_URL="http://127.0.0.1:$port/v1" ANTHROPIC_BASE_URL="http://127.0.0.1:$port"
export RUN_LOG="$work/runs.csv"
"$(Rscript -e 'cat(system.file("bin", "irace", package = "irace"))')" > irace.out 2>&1 || { tail -40 irace.out; exit 1; }
echo "$work"
