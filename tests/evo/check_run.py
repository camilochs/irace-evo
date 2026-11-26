"""Checks a run of tests/evo/run-example.sh against what the paper describes.

    python3 check_run.py WORKDIR [--ef N] [--temperature T] [--top-p P]

Each check prints PASS or FAIL with the evidence; the exit code is the number
of failures. The paper is Chacón Sartori & Blum, "irace-evo: Automatic
Algorithm Configuration Extended with LLM-Based Code Evolution", MIC 2026.
"""
import argparse
import collections
import json
import os
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("--ef", type=int, default=3)
ap.add_argument("--temperature", type=float, default=None)
ap.add_argument("--top-p", type=float, default=None)
ap.add_argument("--refused", action="store_true", help="the fake LLM refused temperature and top_p")
args = ap.parse_args()
os.chdir(args.work)
failures = 0


def check(name, ok, evidence):
    global failures
    print(("PASS " if ok else "FAIL ") + name + " :: " + evidence)
    failures += 0 if ok else 1


# 1. A configuration is a pair (theta, A) (Sect. 2.2): one configuration runs
#    one program for the whole tuning, on every instance it is raced on.
programs = collections.defaultdict(set)
for line in open("runs.csv"):
    cid, exe = line.strip().split(",", 1)
    programs[cid].add(os.path.basename(exe))
changed = {c: sorted(p) for c, p in programs.items() if len(p) > 1}
check("each configuration keeps its code", not changed,
      f"{len(programs)} configurations, {len(changed)} ran more than one program"
      + (f", e.g. {next(iter(changed.items()))}" if changed else ""))

requests = [json.loads(l) for l in open("requests.jsonl")]
generation = []  # (iteration, prompt, body) of each request that asks for a variant
for r in requests:
    body = r["body"]
    prompt = body["messages"][-1]["content"]
    m = re.search(r"Iteration: (\d+)", prompt)
    if m:
        generation.append((int(m.group(1)), prompt, body))
iterations = sorted({i for i, _, _ in generation})
check("the fake LLM was asked for variants", bool(generation),
      f"{len(requests)} requests, {len(generation)} variant requests, iterations {iterations}")


def improve_block(prompt):
    """The code the LLM is told to change: the first code block of the
    function section (the diversity section comes after it)."""
    for marker in ("## COMPLETE SOURCE CODE FOR CONTEXT", "## CURRENT FUNCTION TO IMPROVE"):
        i = prompt.find(marker)
        if i >= 0:
            m = re.search(r"```[a-zA-Z+]*\n(.*?)```", prompt[i:], re.S)
            return marker, m.group(1) if m else ""
    return None, ""


# 2. Always-From-Original (Sect. 2.3): every variant is generated from A0. The
#    fake LLM marks each variant it writes, so a marked function in the block
#    to improve means the prompt started from an earlier variant.
from_variant = [i for i, p, _ in generation if "fake-llm variant" in improve_block(p)[1]]
check("every variant starts from the original code (AFO)", not from_variant,
      f"{len(from_variant)} of {len(generation)} prompts start from an earlier variant"
      + (f" (iterations {sorted(set(from_variant))})" if from_variant else ""))

# 3. Code context window R_i (Sect. 2.4): the whole source file at i = 1,
#    selected fragments for i > 1.
wrong_context = [(i, m) for i, p, _ in generation for m in [improve_block(p)[0]]
                 if (i == 1) != (m == "## COMPLETE SOURCE CODE FOR CONTEXT")]
check("whole file in iteration 1, fragments after (R_i)", not wrong_context,
      f"{len(wrong_context)} of {len(generation)} prompts with the wrong context"
      + (f", e.g. iteration {wrong_context[0][0]}: {wrong_context[0][1]}" if wrong_context else ""))

# 4. Evolution focus E_i (Sect. 2.4): std before iteration ef, aggressive from it.
wrong_focus = []
for i, p, _ in generation:
    m = re.search(r"Improvement intensity needed\*\*: (\w+)", p)
    focus = m.group(1) if m else None
    want = "AGGRESSIVE" if i >= args.ef else "STANDARD"
    if focus != want:
        wrong_focus.append((i, focus))
check(f"standard focus before iteration {args.ef}, aggressive from it (E_i)", not wrong_focus,
      f"{len(wrong_focus)} of {len(generation)} prompts with the wrong focus"
      + (f", e.g. {wrong_focus[:3]}" if wrong_focus else ""))

# 5. LLM hyperparameters Phi (Sect. 2.3): the configured temperature and top_p
#    are the ones sent.
if args.refused:
    # A model that refuses them: the first call carries them, every later one
    # does not, and the run goes on.
    sent = [(b.get("temperature"), b.get("top_p")) for _, _, b in generation]
    ok = sent[0] == (args.temperature, args.top_p) and all(x == (None, None) for x in sent[1:]) and len(iterations) > 1
    check("a model that refuses temperature and top_p is called without them", ok,
          f"sent {collections.Counter(sent)}, iterations {iterations}")
elif args.temperature is not None or args.top_p is not None:
    sent = collections.Counter((b.get("temperature"), b.get("top_p")) for _, _, b in generation)
    want = (args.temperature, args.top_p)
    check("the configured temperature and top_p are sent (Phi)", set(sent) == {want},
          f"wanted {want}, sent {dict(sent)}")

# 6. The API key never reaches a file.
leaks = []
for root, _, files in os.walk("."):
    for f in files:
        path = os.path.join(root, f)
        try:
            if b"fake-key" in open(path, "rb").read() and f != "code-evolution.json":
                leaks.append(path)
        except OSError:
            pass
check("the API key is not written to any log", not leaks, f"found in {leaks}" if leaks else "not found")

# 7. Only the configured provider is called.
paths = collections.Counter(r["path"] for r in requests)
check("only the configured provider is called", len(paths) == 1, f"request paths {dict(paths)}")

sys.exit(failures)
