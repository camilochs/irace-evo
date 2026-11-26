#!/bin/bash
# Follows the README's install steps on a machine with only R on it (the
# rocker/r-ver image), then runs the offline check. Used to verify that the
# instructions work as written:
#
#   docker run --rm -v "$PWD":/src:ro rocker/r-ver:4.4.2 /src/tests/evo/fresh-install.sh
set -euo pipefail
apt-get update -qq > /dev/null
# What the README lists for Linux: Python with its shared library (which
# reticulate binds to) and venv, a C++ compiler, and the libraries two R
# packages compile against (fs: libuv; png, for reticulate: libpng).
apt-get install -y -qq --no-install-recommends python3 python3-dev python3-venv g++ make libuv1-dev libpng-dev zlib1g-dev bc procps > /dev/null
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
