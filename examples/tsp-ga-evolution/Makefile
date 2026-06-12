# Makefile for TSP-GA irace-evo Example

CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall
SRCDIR = src
BINDIR = bin
TARGET = $(BINDIR)/brkga
SOURCE = $(SRCDIR)/brkga.cpp

.PHONY: all clean test install

all: $(TARGET)

$(BINDIR):
	mkdir -p $(BINDIR)

$(TARGET): $(SOURCE) | $(BINDIR)	
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -rf $(BINDIR)
	rm -f *.stdout *.stderr *.Rdata
	rm -rf logs/*

test: $(TARGET)
	./$(TARGET) --instance instances/att48.tsp --generations 300 --population-size 100

install:
	@echo "Installing dependencies..."
	@echo "Step 1: Install R packages (excluding irace)"
	R -e "install.packages(c('reticulate', 'jsonlite'))"
	@echo "Step 2: Install Python packages"
	pip install openai anthropic requests
	@echo "Step 3: Install irace-evo from source"
	@echo "Run: cd ../../ && R CMD INSTALL ."
	@echo "Step 4: Set environment variable"
	@echo "export OPENAI_API_KEY='your-key-here'"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - g++ with C++17 support"
	@echo "  - R >= 4.0"
	@echo "  - Python >= 3.7"
	@echo "  - OpenAI or Anthropic API key"

help:
	@echo "Available targets:"
	@echo "  all     - Compile the TSP-GA algorithm"
	@echo "  clean   - Remove compiled files and logs"
	@echo "  test    - Run a quick test of the algorithm"
	@echo "  install - Show installation requirements"
	@echo "  help    - Show this help message"