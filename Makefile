SECONDARY_OUTPUT = output/demand_by_birth.png output/demand_by_time.csv
# NB: main compute and post-processing are not separated here; it's run_scenarios.py for both
POSTPROCESSING_SCRIPT = scripts/run_scenarios.py
MAIN_OUTPUT = output/results.csv
MAIN_SCRIPT = scripts/run_scenarios.py
PACKAGE_CODE = drugdemand/__init__.py drugdemand/nirsevimab.py
SCENARIOS = input/scenarios.yaml
DATA_INPUT = input/births.csv input/weights.csv
PREPROCESSING_SCRIPT = scripts/preprocess.py
RAW_DATA = data/Natality,\ 2016-2022\ expanded.txt data/weights.csv data/hhs_regions.yaml

.PHONY: clean

all: $(SECONDARY_OUTPUT)

# POSTPROCESSING --------------------------------------------------------------
$(SECONDARY_OUTPUT): $(MAIN_OUTPUT) $(POSTPROCESSING_SCRIPT)
	python $(POSTPROCESSING_SCRIPT)

# MAIN COMPUTATION ------------------------------------------------------------
$(MAIN_OUTPUT): $(DATA_INPUTS) $(SCENARIOS) $(MAIN_SCRIPT) $(PACKAGE_CODE)
	python $(MAIN_SCRIPT)

# PREPROCESSING ---------------------------------------------------------------
$(INPUTS): $(PREPROCESSING_SCRIPT) $(RAW_DATA)
	python $(PREPROCESSING_SCRIPT)

$(SCENARIOS): scripts/write_scenarios.py
	python scripts/write_scenarios.py

# Data history ----------------------------------------------------------------
# not intended to be run by the user; kept here for data history tracking
data/weights.csv: scripts/pct_heavier_by_age.R
	Rscript scripts/pct_heavier_by_age.R

clean:
	rm -f input/* output/*
