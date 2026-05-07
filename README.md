# From CP Modeling to Preference Elicitation in HMLV Assembly Problems

This repository contains code and experiment artifacts for the paper
**"From CP Modeling to Preference Elicitation in HMLV Assembly Problems"**.

> **Warning**
> This branch is experimental. It includes a `NoOverlapOptional` formulation
> that was not available before the paper submission. Preliminary results in
> this branch indicate that `NoOverlapOptional` is more effective than the
> formulation reported in the submitted paper, so results from this branch
> should be interpreted as post-submission exploratory evidence.

The current branch is a reduced version of the original experiment repository.
It keeps the CP scheduling model, benchmark data, benchmark result artifacts,
PAR2 plotting script, visualization helpers, and preference-elicitation support
classes. Several earlier top-level scripts for running and aggregating the full
preference-elicitation experiments have been removed.

## Repository Structure

```text
.
|-- data/
|   |-- cp_model_data/          # CP benchmark instances
|   |-- normalization/          # Ideal/nadir values for normalized objectives
|   |-- data_training_*.json    # Training topologies used by the model
|   |-- solution_training_*.csv # Reference preferred solutions
|   `-- user_preferences.csv    # Simulated user objective weights
|-- cp_model_results/           # Stored CP benchmark result artifacts
|-- utils/
|   |-- jobshop_model_final.py  # CP model for assembly and transport scheduling
|   |-- CPE.py                  # Constructive Preference Elicitation class
|   |-- DWS.py                  # Dynamic Weight Setting class
|   |-- utility.py              # Bounds, solving, plotting, and helper routines
|   |-- utility_classes.py      # Oracle and experiment helper classes
|   `-- visualization.py        # Plotly topology and Gantt visualization helpers
|-- solve_cp_model_data.py      # Batch solver for CP benchmark instances
|-- plot_par2.py                # PAR2 plot generation from benchmark CSV files
|-- visualizer.ipynb            # Notebook for inspecting schedules/solutions
|-- requirements.txt
`-- LICENSE
```

## Model Overview

The CP model is implemented in `utils/jobshop_model_final.py`, in the
`FJTransportProblemFinal` class. It models a high-mix low-volume assembly
planning problem with alternative workstations, operators, mobile robots,
conveyor belts, and transport decisions.

Each product is represented as a route containing processing operations and
transport markers. The model expands transport markers into explicit transport
tasks between consecutive processing operations. Processing and transport tasks
can be assigned to alternative resources:

- automated workstations;
- human workstations and skilled operators;
- mobile robots;
- conveyor belts;
- zero-duration internal transports when consecutive operations can remain at
  the same workstation.

The model optimizes weighted combinations of five objectives:

- `makespan`
- `workstations`
- `employees`
- `robots`
- `employee_time`

The branch supports two resource-capacity formulations through
`use_no_overlap`:

- `False`: pooled resources are modeled with `CumulativeOptional`;
- `True`: individual operators and robots are modeled with `NoOverlapOptional`.

This `NoOverlapOptional` variant is the experimental post-submission
formulation called out in the warning above.

## Data and Results

The main input files are:

- `data/cp_model_data/data_training_<type>_<idx>.json`: CP benchmark instances
  solved by `solve_cp_model_data.py`;
- `data/data_training_<n>.json`: training topology files used by the model and
  visualization tooling;
- `data/user_preferences.csv`: simulated user objective weights;
- `data/solution_training_1.csv` and `data/solution_training_2.csv`: reference
  preferred solutions;
- `data/normalization/*_optimal_values.csv` and
  `data/normalization/*_nadir_maximization.csv`: objective bounds used for
  normalized multi-objective solving.

Stored benchmark CSV artifacts are under `cp_model_results/`, grouped by solver
and formulation. New runs from `solve_cp_model_data.py` write CSV files under
`data/cp_model_results/<solver>/`.

## Setup

Create and activate a Python environment, then install the listed
dependencies:

```bash
pip install -r requirements.txt
```

The model supports the solver backends exposed through CPMpy. OR-Tools is the
default solver used by `solve_cp_model_data.py`; using Gurobi requires a working
Gurobi installation and license.

## Solve CP Benchmark Instances

Run the CP model over all benchmark JSON files and selected user preferences:

```bash
python solve_cp_model_data.py --symmetry --lowerbound --solver ortools
```

Filter to a specific benchmark type:

```bash
python solve_cp_model_data.py --type 1 --symmetry --lowerbound --solver ortools
```

Use the experimental `NoOverlapOptional` formulation:

```bash
python solve_cp_model_data.py --type 2 --symmetry --lowerbound --no_overlap --solver ortools
```

The script currently evaluates user preference rows 5-14 and 30-39 from
`data/user_preferences.csv`, with a 600 second timeout per solve. Each run writes
one CSV per instance/configuration.

## Plot PAR2 Results

`plot_par2.py` computes PAR2 scores from benchmark CSV files matching:

```text
data/cp_model_results/**/solution_data_training_2_*.csv
```

The plotting script expects those files to be arranged in solver/formulation
subdirectories, for example
`data/cp_model_results/ortools/nooverlap/solution_data_training_2_1_...csv`.
Stored artifacts under `cp_model_results/` need to be copied, moved, or the glob
in `plot_par2.py` needs to be adjusted before plotting them.

Run:

```bash
python plot_par2.py
```

## Visualization

`utils/visualization.py` contains helpers for:

- plotting workstation topology graphs from JSON data;
- plotting Gantt charts for computed schedules.

`visualizer.ipynb` provides an interactive notebook for inspecting schedules and
solution structure.

## License

This project is distributed under the terms in `LICENSE`.
