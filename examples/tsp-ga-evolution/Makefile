# Makefile for the irace-evo example (BRKGA for the Longest Run Subsequence problem)

CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall
SRCDIR = src
BINDIR = bin
TARGET = $(BINDIR)/brkga
SOURCE = $(SRCDIR)/brkga.cpp

.PHONY: all clean test help

all: $(TARGET)

$(BINDIR):
	mkdir -p $(BINDIR)

$(TARGET): $(SOURCE) | $(BINDIR)	
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -rf $(BINDIR)
	rm -f *.stdout *.stderr *.Rdata .irace_evo_*
	rm -rf logs irace-evo-sources irace-evo-llm-logs

test: $(TARGET)
	./$(TARGET) -i tuning_instances/len_1000_sigma8_0.txt -t 2

help:
	@echo "Available targets:"
	@echo "  all     - Compile the original BRKGA (bin/brkga)"
	@echo "  clean   - Remove compiled files and logs"
	@echo "  test    - Run a quick test of the algorithm"
	@echo "  help    - Show this help message"