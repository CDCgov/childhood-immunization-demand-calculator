SECONDARY_OUTPUT = output/demand_by_birth.png output/demand_by_time.csv
MAIN_OUTPUT = output/results.csv
PACKAGE_CODE = drugdemand/__init__.py drugdemand/nirsevimab.py
SCENARIOS = input/scenarios.yaml
INPUT = input/births.csv input/weights.csv
RAW_DATA = data/Natality,\ 2016-2022\ expanded.txt data/weights.csv

.PHONY: clean

all: $(SECONDARY_OUTPUT)

# POSTPROCESSING --------------------------------------------------------------
$(SECONDARY_OUTPUT): scripts/postprocess.py $(MAIN_OUTPUT) $(POSTPROCESSING_SCRIPT)
	python $<

# MAIN COMPUTATION ------------------------------------------------------------
$(MAIN_OUTPUT): scripts/run_scenarios.py $(INPUT) $(SCENARIOS) $(PACKAGE_CODE)
	python $<

# PREPROCESSING ---------------------------------------------------------------
$(INPUT): scripts/preprocess.py $(RAW_DATA)
	python $<

$(SCENARIOS): scripts/create_scenarios.py
	python $<

# Data history ----------------------------------------------------------------
# not intended to be run by the user; kept here for data history tracking
data/weights.csv: scripts/pct_heavier_by_age.R
	Rscript $<

clean:
	rm -f input/* output/*
