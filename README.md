# From CP Modeling to Preference Elicitation in HMLV Assembly Problems

This repository contains the code and experiment artifacts for the paper
**"From CP Modeling to Preference Elicitation in HMLV Assembly Problems"**.

The project models a high-mix low-volume (HMLV) assembly planning problem as a
constraint programming (CP) scheduling problem with alternative workstations,
operators, mobile robots, conveyor belts, and transport decisions. On top of the
CP model, the repository implements preference elicitation procedures that learn
objective trade-offs from simulated user feedback.

The main experimental objectives are:

- build and solve flexible job-shop assembly instances with transport resources;
- compare CP model variants such as cumulative versus no-overlap resource
  constraints, symmetry breaking, and custom lower bounds;
- compute normalization bounds for multi-objective optimization;
- run preference elicitation with Constructive Preference Elicitation (CPE) and
  Dynamic Weight Setting (DWS);
- aggregate regret curves and generate the figures used in the paper.

## Repository Structure

```text
.
|-- data/
|   |-- cp_model_data/          # CP model evaluation instances
|   |-- normalization/          # Ideal/nadir values used for normalization
|   |-- data_training_*.json    # Topologies considered for preference elicitation
|   |-- solution_training_*.csv # Preferred solutions per simulated user
|   `-- user_preferences.csv    # Simulated user objective weights
|-- cp_model_results/           # CP benchmark solve outputs
|-- results/
|   |-- pref_eliciation/        # Preference elicitation experiment outputs
|   |-- tuning/                 # Hyperparameter tuning outputs
|   `-- *.csv, *.png            # Aggregated tables and plots
|-- utils/
|   |-- jobshop_model_final.py  # CP model for assembly and transport scheduling
|   |-- CPE.py                  # Constructive Preference Elicitation
|   |-- DWS.py                  # Dynamic Weight Setting
|   |-- utility_classes.py      # Oracle and experiment helper classes
|   |-- utility.py              # Solving, bounds, plotting, and helper routines
|   `-- visualization.py        # Plotly visualization utilities
|-- solve_cp_model_data.py      # Batch solving for CP model experiments
|-- compute_normalization_bounds.py
|-- run_cp.py                   # CPE runs with lexicographic preferences
|-- run_cp_W.py                 # CPE runs with uniformly generated weights
|-- run_dws.py                  # DWS runs with lexicographic preferences
|-- run_dws_w.py                # DWS runs with uniformly generated weights
|-- aggregate_results.py        # Extract relevant preference elicitation results
|-- plot_regret_CPE.py          # Plot CPE regret comparisons from CSV results
`-- visualizer.ipynb            # Notebook for inspecting schedules/solutions
```

## Model Overview

The CP model is implemented in `utils/jobshop_model_final.py`, in the
`FJTransportProblemFinal` class. That file contains the full scheduling model:
JSON data loading, transport expansion, decision-variable creation, constraints,
objective expressions, and the solve interface used by CPE and DWS.

Each product in an orderbook is represented as a sequence of assembly operations
and transport markers. The model expands transport markers into explicit
transport actions between consecutive operations. Processing and transport tasks
can be assigned to alternative resources:

- automated workstations;
- human operators with skills and processing durations;
- mobile robots for transport;
- conveyor belts where the topology supports a transport move;
- zero-duration internal transports when consecutive operations can stay on the
  same workstation.

The model optimizes weighted combinations of five objectives:

- `makespan`
- `workstations`
- `employees`
- `robots`
- `employee_time`

Timing objectives are reported in hours in the exported objective dictionaries.

The model file includes:

- expansion of `T` markers in each product route into explicit transport tasks
  between consecutive processing operations;
- assignment variables for automatic workstations, human workstations, skill
  pools, mobile robots, conveyors, and zero-duration internal transports;
- start-time, duration, end-time, sequencing, assignment, resource-capacity,
  no-overlap/cumulative, conveyor-consistency, internal-transport, and optional
  symmetry-breaking constraints;
- objective expressions for `makespan`, number of used workstations, number of
  used employees, number of active robots, and cumulative employee work time;
- weighted and normalized objective solving, plus diversification/image
  constraints used during preference elicitation.

## Data

The main input files are:

- `data/data_training_<n>.json`: topology instances used by the preference
  elicitation scripts. The index `<n>` identifies the topology: topology 1 is
  the easier setting, while topology 2 is more complex;
- `data/cp_model_data/data_training_<type>_<idx>.json`: instances used to
  evaluate the CP model formulation with `solve_cp_model_data.py`;
- `data/user_preferences.csv`: simulated user objective weights;
- `data/solution_training_1.csv`: preferred reference solutions generated from
  lexicographic objective orders;
- `data/solution_training_2.csv`: preferred reference solutions generated from
  Das-Dennis weight vectors;
- `data/normalization/*_optimal_values.csv` and
  `data/normalization/*_nadir_maximization.csv`: objective bounds used by
  normalized multi-objective solving.

Preference elicitation result folders use the following naming convention:

- `results_CPE_lex_<n>`: CPE results for topology `<n>` with lexicographic-order
  reference preferences;
- `results_CPE_W_<n>`: CPE results for topology `<n>` with uniformly generated
  weight-vector preferences;
- `results_DWS_<n>`: DWS results for lexicographic-order reference preferences;
- `results_DWS_w_<n>`: DWS results for uniformly generated weight-vector
  preferences.

Normalization labels in the scripts map to the paper terminology as follows:
`base` is the default normalization, `local` is the local update normalization,
and `custom` is the SNOW normalization reported in the paper.

The `results/` directory contains the aggregated result CSV files and generated
plots used for the paper figures.

## Common Workflows

### 1. Solve CP Benchmark Instances

Run the CP model over all benchmark JSON files and selected user preferences:

```bash
python solve_cp_model_data.py --symmetry --lowerbound --solver ortools
```

Examples:

```bash
# Only training type 1, cumulative constraints
python solve_cp_model_data.py --type 1 --symmetry --lowerbound --solver ortools

# Use no-overlap constraints instead of cumulative constraints
python solve_cp_model_data.py --type 2 --symmetry --lowerbound --no_overlap --solver ortools
```

The script writes one CSV per instance/configuration under
`cp_model_results/<solver>/`.

### 2. Compute Normalization Bounds

Preference elicitation with base normalization expects ideal and nadir values in
`data/normalization/`.

```bash
python compute_normalization_bounds.py
```

The script optimizes each objective individually, both in minimization and
maximization mode, then writes:

- `data/normalization/data_training_2_optimal_values.csv`
- `data/normalization/data_training_2_nadir_maximization.csv`

If you add another training instance, update the `datasets` list in
`compute_normalization_bounds.py`.

### 3. Run CPE Preference Elicitation

Run comparison-based preference elicitation for the lexicographic preference
users:

```bash
python run_cp.py --training 1 --normalization base --diversification base --disjunctive True
```

Other supported modes:

```bash
python run_cp.py --training 2 --normalization local --diversification UCB --disjunctive True
python run_cp.py --training 2 --normalization custom --diversification base --disjunctive False
```

`run_cp.py --training <n>` writes to `results_CPE_lex_<n>`, where `<n>` is the
corresponding `data/data_training_<n>.json` instance.

`run_cp_W.py` runs the uniformly generated weight users and writes to
`results_CPE_W_<n>`.

Each run creates per-user folders containing:

- `dataset.csv`: queried solution pairs, oracle labels, solve times, and regret;
- `regret.csv`: periodic regret evaluation and learned weights.

### 4. Run DWS Preference Elicitation

Run DWS for the lexicographic preference users on training instance 2:

```bash
python run_dws.py --normalization base
python run_dws.py --normalization custom
```

`run_dws_w.py` runs the uniformly generated weight users with the corresponding
tuned hyperparameters.

Each run writes:

- `solve_history.csv`: all inner solves, bounds, weights, and regrets;
- `regret.csv`: periodic regret evaluation.

### 5. Aggregate and Plot Results

Extract the relevant result information from one or more preference elicitation
experiment roots:

```bash
python aggregate_results.py --directories results_CPE_lex_1 results_DWS_2
```

This writes:

```text
results/results.csv
```

Generate grouped bar plots from an aggregated CSV:

```bash
python plot_regret_CPE.py \
  --input results/results.csv \
  --output results/tuning_comparison.png \
  --individual
```

Additional plotting scripts used for the paper include:

- `plot_DWS_CPE.py`
- `plot_regret_CPE.py`: generates grouped regret bar plots for CPE variants
  across normalization methods and query budgets;
- `plot_par2.py`
- `compute_initial_query_stats.py`
- `compute_dws_stats.py`

## License

This project is distributed under the terms in `LICENSE`.
