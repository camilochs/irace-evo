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
echo "== python example (anthropic)"
tests/evo/run-python-example.sh anthropic /out/python > /dev/null || { tail -30 /out/python/irace.out; status=1; }
python3 tests/evo/check_run.py /out/python --temperature 1.0 --top-p 0.9 || status=1
echo "== java example (anthropic)"
tests/evo/run-java-example.sh anthropic /out/java > /dev/null || { tail -30 /out/java/irace.out; status=1; }
python3 tests/evo/check_run.py /out/java --temperature 1.0 --top-p 0.9 || status=1
# Provider APIs change: a thinking block first, an old token-limit name,
# and a provider that fails every call (irace must stop and say why).
echo "== anthropic, reply with a thinking block first"
FAKE_THINKING=1 tests/evo/run-example.sh anthropic /out/thinking > /dev/null || { tail -30 /out/thinking/irace.out; status=1; }
python3 tests/evo/check_run.py /out/thinking --temperature 1.0 --top-p 0.9 || status=1
echo "== openai, model that only takes max_tokens"
FAKE_OLD_OPENAI=1 tests/evo/run-example.sh openai /out/oldopenai > /dev/null || { tail -30 /out/oldopenai/irace.out; status=1; }
python3 tests/evo/check_run.py /out/oldopenai --old-openai || status=1
echo "== provider down"
if FAKE_DOWN=1 tests/evo/run-example.sh anthropic /out/down > /dev/null 2>&1; then
  echo "FAIL a run whose every LLM call fails should stop"; status=1
elif grep -q "every call to the LLM failed; the last error was: .*invalid x-api-key" /out/down/irace.out; then
  echo "PASS a provider that fails every call stops irace with its error :: $(grep -o 'every call to the LLM failed.\{0,120\}' /out/down/irace.out | head -1)"
else
  echo "FAIL the run stopped without the provider's error"; tail -5 /out/down/irace.out; status=1
fi
exit $status
