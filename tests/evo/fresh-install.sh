#!/bin/bash
# Follows the README's install steps on a machine with only R on it (the
# rocker/r-ver image), then runs the offline check. Used to verify that the
# instructions work as written:
#
#   docker run --rm -v "$PWD":/src:ro rocker/r-ver:4.4.2 /src/tests/evo/fresh-install.sh
set -euo pipefail
apt-get update -qq > /dev/null
# Python, a C++ compiler, and libpng (reticulate depends on the png package,
# which compiles against it on Linux).
apt-get install -y -qq --no-install-recommends python3 python3-venv g++ make bc procps libpng-dev zlib1g-dev > /dev/null
cp -R /src /irace-evo && cd /irace-evo

echo '$ python3 -m venv ~/.venvs/irace-evo'
python3 -m venv ~/.venvs/irace-evo
echo '$ export RETICULATE_PYTHON=~/.venvs/irace-evo/bin/python'
export RETICULATE_PYTHON=~/.venvs/irace-evo/bin/python
echo '$ ./install-irace.sh'
./install-irace.sh > /tmp/install.log 2>&1 || { tail -30 /tmp/install.log; exit 1; }
tail -4 /tmp/install.log
export PATH="$(Rscript -e 'cat(system.file("bin", package = "irace"))'):$PATH"
echo '$ tests/evo/run-example.sh anthropic /tmp/evo-run'
tests/evo/run-example.sh anthropic /tmp/evo-run
echo '$ python3 tests/evo/check_run.py /tmp/evo-run --temperature 1.0 --top-p 0.9'
python3 tests/evo/check_run.py /tmp/evo-run --temperature 1.0 --top-p 0.9
