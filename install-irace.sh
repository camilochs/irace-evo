#!/bin/sh
# Install irace-evo (the R package keeps the name irace): the R packages it
# needs, the package itself, and the Python packages its LLM side imports.
set -e
Rscript -e 'pkgs <- c("R6", "codetools", "data.table", "fs", "matrixStats", "spacefillr", "withr", "reticulate", "jsonlite");
            missing <- setdiff(pkgs, rownames(installed.packages()));
            if (length(missing)) install.packages(missing, repos = "https://cloud.r-project.org")'
R CMD INSTALL .
# The Python that R will use: RETICULATE_PYTHON when set (a virtual
# environment, say), python3 otherwise.
"${RETICULATE_PYTHON:-python3}" -m pip install -r inst/python/requirements.txt
bin="$(Rscript -e 'cat(system.file("bin", package = "irace"))')"
echo
echo "Installed. The irace command is $bin/irace; to call it as 'irace':"
echo "  export PATH=\"$bin:\$PATH\""
