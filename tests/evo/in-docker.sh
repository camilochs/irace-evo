#!/bin/bash
# Builds the package from /src and runs the end-to-end check for each
# provider; results land in /out/<provider>.
set -u
cp -R /src /build && cd /build && R CMD INSTALL . > /out/install.log 2>&1 || { tail -20 /out/install.log; exit 1; }
status=0
for provider in ${PROVIDERS:-openai anthropic}; do
  echo "== $provider"
  tests/evo/run-example.sh "$provider" "/out/$provider" > /dev/null || { tail -30 "/out/$provider/irace.out"; status=1; continue; }
  python3 tests/evo/check_run.py "/out/$provider" --temperature 1.0 --top-p 0.9 || status=1
done
# A model that takes no temperature or top_p (recent Claude models, OpenAI
# reasoning models).
echo "== anthropic, model refusing temperature and top_p"
FAKE_REFUSE_SAMPLING=1 tests/evo/run-example.sh anthropic /out/refusing > /dev/null || { tail -30 /out/refusing/irace.out; status=1; }
python3 tests/evo/check_run.py /out/refusing --temperature 1.0 --top-p 0.9 --refused || status=1
exit $status
