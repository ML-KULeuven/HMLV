import math
import os
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from cpmpy.tools import ParameterTuner, GridSearchTuner


import os
import re
import cpmpy as cp
from utils.visualization import plot_solution_gantt


def solve_and_save_all_optimal_schedules(
    problem,
    solver_name="ortools",
    solutions_dir="solutions",
    base_name="schedule",
    max_solutions=None,
):
    """
    Solve the problem to optimality and enumerate up to `max_solutions`
    optimal schedules. Each schedule is plotted and saved in `solutions_dir`.

    If `max_solutions=None`, enumerate *all* optimal solutions.

    Parameters
    ----------
    problem : FJTransportProblem
        Your scheduling problem instance.
    solver_name : str
        Solver for CP-SAT via cpmpy (e.g. "ortools").
    solutions_dir : str
        Directory to store PNG schedule images.
    base_name : str
        Base filename prefix (e.g., "schedule_000.png").
    max_solutions : int or None
        Maximum number of optimal solutions to enumerate.
        None means "no limit".

    Returns
    -------
    int
        Number of optimal schedules saved.
    """
    # --- Build model ---
    problem.make_model()

    # --- Solve once to get optimal makespan ---
    solver = cp.SolverLookup.get(solver_name,problem.model)
    if not solver.solve():
        print("No feasible solution found.")
        return 0

    optimal_ms = int(problem.makespan.value())
    print(f"Optimal makespan: {optimal_ms}")

    # Fix makespan to the optimal value for enumeration
    problem.model += (problem.makespan == optimal_ms)

    # --- Prepare output folder ---
    os.makedirs(solutions_dir, exist_ok=True)

    # Determine next available numeric ID
    existing_files = [
        f for f in os.listdir(solutions_dir)
        if f.startswith(base_name) and f.endswith(".png")
    ]
    used_ids = []
    for f in existing_files:
        m = re.search(r"(\d+)", f)
        if m:
            used_ids.append(int(m.group(1)))
    next_id = max(used_ids) + 1 if used_ids else 0

    # --- Gather all Z-vars for blocking ---
    Z_vars = [
        problem.Z[item][op][agent]
        for item in problem.items
        for op in problem.item_operations[item]
        for agent in problem.Z[item][op]
    ]

    # --- Enumerate optimal solutions ---
    count = 0

    while True:
        # Try solving with current constraints
        solver = cp.SolverLookup.get(solver_name,problem.model)
        if not solver.solve():
            break  # no more optimal solutions

        # Check makespan correctness
        assert int(problem.makespan.value()) == optimal_ms

        # --- Save plot ---
        filename = os.path.join(solutions_dir, f"{base_name}_{next_id:03d}.png")
        print(f"Saving optimal solution #{count} → {filename}")

        plot_solution_gantt(problem, file_png=filename, show=False)

        count += 1
        next_id += 1

        if max_solutions is not None and count >= max_solutions:
            break

        # --- Block this solution ---
        # At least one Z-var must change
        problem.model += cp.any(z != int(z.value()) for z in Z_vars)

    print(f"Total optimal solutions saved: {count}")
    return count

def tune(problem,max_tries=100,grid=False,time_limit=60):
    if grid:
        tuner_grid = GridSearchTuner("ortools", problem)
        best_param = tuner_grid.tune(max_tries=max_tries,time_limit=time_limit)
    else:
        tuner_param = ParameterTuner("ortools", problem)
        best_param = tuner_param.tune(max_tries=max_tries,time_limit=time_limit)
    print('Tuning done')
    return best_param


def ensure_directory_exists(directory_path):
    """
    Create directory if it doesn't exist.

    Args:
        directory_path (str): Path to the directory to create
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)

def plot_comparison_sym_csv(csv_filepath, output_dir="results", filename="comparison_plot_from_csv.png",
                            figsize=(12, 8), bar_width=0.35):
    """
    Create a bar chart comparison plot from a previously saved CSV file.

    Args:
        csv_filepath (str): Path to the CSV file to read
        output_dir (str): Directory to save the plot (default: "results")
        filename (str): Name of the plot file (default: "comparison_plot_from_csv.png")
        figsize (tuple): Figure size (width, height) in inches (default: (12, 8))
        bar_width (float): Width of the bars (default: 0.35)
    """
    # Create output directory if it doesn't exist
    ensure_directory_exists(output_dir)

    # Read CSV data
    items = []
    time_sym = []
    time_no_sym = []

    try:
        with open(csv_filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                items.append(int(row['number_of_items']))
                # Handle empty values
                time_sym.append(float(row['time_symmetries']) if row['time_symmetries'] else None)
                time_no_sym.append(float(row['time_no_symmetries']) if row['time_no_symmetries'] else None)
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_filepath}")
        return None
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)

    # Set up bar positions using actual item values
    x = np.array(items)

    # Create bars
    bars1 = ax.bar(x - bar_width / 2, time_sym, bar_width,
                   label='With Symmetries', alpha=0.8, color='skyblue')
    bars2 = ax.bar(x + bar_width / 2, time_no_sym, bar_width,
                   label='Without Symmetries', alpha=0.8, color='lightcoral')

    # Customize the plot
    ax.set_xlabel('Number of Items', fontsize=12)
    ax.set_ylabel('Solving Time (seconds)', fontsize=12)
    ax.set_title('Symmetries vs No-Symmetries Solving Time Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(items)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels on bars
    def add_value_labels(bars):
        for bar in bars:
            if bar.get_height() is not None:
                height = bar.get_height()
                ax.annotate(f'{height:.2f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)

    add_value_labels(bars1)
    add_value_labels(bars2)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save the plot
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Comparison plot from CSV saved to: {filepath}")

    # Show the plot
    plt.show()

    def load_tuning_params(json_filepath):
        """
        Load tuning parameters from a JSON file.

        Args:
            json_filepath (str): Path to the JSON file to read

        Returns:
            dict: Dictionary containing the tuning parameters
        """
        try:
            with open(json_filepath, 'r', encoding='utf-8') as jsonfile:
                params = json.load(jsonfile)
            print(f"Tuning parameters loaded from: {json_filepath}")
            return params
        except FileNotFoundError:
            print(f"Error: JSON file not found at {json_filepath}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return None
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return None


from collections import defaultdict, deque
from typing import Any, Callable, Dict, Iterable, Hashable


# ---- Core generic helpers -------------------------------------------------


def _critical_path_bound(
    tasks: Iterable[Any],
    duration_of: Callable[[Any], int],
    successors_of: Callable[[Any], Iterable[Any]],
) -> int:
    """Precedence-based LB: longest path in the DAG (sum of durations)."""
    tasks = list(tasks)

    # Build indegrees
    indegree: Dict[Any, int] = {t: 0 for t in tasks}
    for t in tasks:
        for succ in successors_of(t):
            indegree[succ] = indegree.get(succ, 0) + 1

    # Earliest completion of each task
    earliest_completion: Dict[Any, int] = {t: duration_of(t) for t in tasks}

    # Topological order via Kahn’s algorithm
    queue = deque([t for t in tasks if indegree.get(t, 0) == 0])

    while queue:
        t = queue.popleft()
        for succ in successors_of(t):
            # relax longest-path DP
            cand = earliest_completion[t] + duration_of(succ)
            if cand > earliest_completion.get(succ, 0):
                earliest_completion[succ] = cand
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)

    return max(earliest_completion.values()) if earliest_completion else 0


def _resource_load_bound_single_machine(
    tasks: Iterable[Any],
    duration_of: Callable[[Any], int],
    machine_of: Callable[[Any], Hashable],
) -> int:
    """
    Simple machine-load LB:
      LB = max_m sum_{i on m} p_i
    assuming unary machines (capacity = 1).
    """
    tasks = list(tasks)
    load_per_machine: Dict[Hashable, int] = defaultdict(int)

    for t in tasks:
        m = machine_of(t)
        if m is None:
            continue
        load_per_machine[m] += duration_of(t)

    return max(load_per_machine.values()) if load_per_machine else 0


def _job_chain_bound(
    tasks: Iterable[Any],
    duration_of: Callable[[Any], int],
    job_of: Callable[[Any], Hashable],
) -> int:
    """
    Job-based LB:
      LB = max_j sum_{i in job j} p_i
    """
    tasks = list(tasks)
    load_per_job: Dict[Hashable, int] = defaultdict(int)

    for t in tasks:
        j = job_of(t)
        if j is None:
            continue
        load_per_job[j] += duration_of(t)

    return max(load_per_job.values()) if load_per_job else 0


# ---- Public function you will actually call -------------------------------


def compute_makespan_lower_bound(inst):
    """
    Returns an integer lower bound on makespan.
    Supports both:
      - old API: inst.tasks with task.duration, task.successors
      - FJTransportProblemFinal: tasks are (item_id, op_name)
    """

    # ----------------------------
    # Task extraction
    # ----------------------------
    def _tasks():
        if hasattr(inst, "tasks"):
            return inst.tasks

        # FJTransportProblemFinal style
        if hasattr(inst, "items") and hasattr(inst, "item_operations"):
            return [(i, op) for i in inst.items for op in inst.item_operations[i]]

        raise AttributeError(f"Instance {type(inst).__name__} has no recognizable task structure")

    tasks = _tasks()

    # ----------------------------
    # Duration lower bound per task
    # ----------------------------
    def _duration_of(task):
        # old API: task object with .duration
        if hasattr(task, "duration"):
            return int(task.duration)

        # FJTransportProblemFinal: task = (item_id, op_name)
        i, op = task

        # Transport op: min over feasible transport choices
        if hasattr(inst, "is_transport") and inst.is_transport(op):
            durs = []

            # per-agent (conveyors/internal WS)
            for a, z in inst.Z_tr[i][op].items():
                # pooled ids are handled below
                if a == "robot_pool" or str(a).startswith("skill_"):
                    continue
                durs.append(int(inst.dict_agent_actions[a][op]))

            # robot pool
            if "robot_pool" in inst.Z_tr[i][op]:
                durs.append(int(inst.robot_T_duration))

            # skill pools for transport
            for a in inst.Z_tr[i][op].keys():
                if str(a).startswith("skill_"):
                    skill_token = str(a)[len("skill_"):]
                    skill_key = skill_token
                    if skill_key not in inst.skill_durations:
                        try:
                            skill_key = int(skill_token)
                        except ValueError:
                            pass
                    durs.append(int(inst.skill_durations[skill_key]["T"]))

            if not durs:
                raise ValueError(f"No feasible duration found for transport {op} of item {i}")
            return min(durs)

        # Processing op: min over feasible auto durations and skill durations
        durs = []

        # auto WS durations
        for ws_id in inst.Z_auto_ws[i][op].keys():
            durs.append(int(inst.workstations_auto[ws_id]["durations"][op]))

        # human skill durations
        for skill in inst.Z_skill[i][op].keys():
            durs.append(int(inst.skill_durations[skill][op]))

        if not durs:
            raise ValueError(f"No feasible duration found for processing {op} of item {i}")
        return min(durs)

    # ----------------------------
    # Successors (precedence edges)
    # ----------------------------
    def _successors_of(task):
        # old API: task object with .successors or similar
        if hasattr(task, "successors"):
            return list(task.successors)

        # FJTransportProblemFinal: immediate successor in the item route
        i, op = task
        ops = inst.item_operations[i]
        idx = ops.index(op)
        if idx == len(ops) - 1:
            return []
        return [(i, ops[idx + 1])]

    # ---- now keep your existing bound computation ----
    lb_prec = _critical_path_bound(tasks, _duration_of, _successors_of)

    # If you have other bound components (resource bound, etc.), keep them,
    # but ensure they also use the adapted duration/task representation.

    return lb_prec


def create_folders(directory):
    """
    Create nested directories, making parent directories as needed.

    Args:
        directory: String path of directories to create
    """
    folders = directory.split(os.path.sep)
    current_path = ''
    if not folders[0]:
        current_path = os.path.sep  # Set the current path to root
        folders = folders[1:]
    for folder in folders:
        current_path = os.path.join(current_path, folder)
        if not os.path.exists(current_path):
            os.mkdir(current_path)

def compute_diversification_weights(diversification, objectives, trade_offs, c_ucb=2):
    w_div = {}
    for obj in objectives:
        if diversification=='base':
            w_div[obj] = 1
        elif diversification=='weighted':
            w_div[obj] = objectives[obj]
        elif diversification=='UCB':
            w_div[obj] = compute_ucb(obj,trade_offs,c_ucb)
    print(f'WEIGHTS DIVERSIFICATION: {w_div}')
    return w_div


def compute_ucb(obj,dataset,c=2):
    # Remove rows with picked == -1
    diff_counts = 0
    picked_better_counts = 0

    filtered = [row for row in dataset if row[3] != -1]
    for _, obj1, obj2, picked, *_ in filtered:
        v1 = obj1[obj]
        v2 = obj2[obj]
        if v1 != v2:
            diff_counts += 1
        if picked == 0 and v1 < v2:
            picked_better_counts += 1
        elif picked == 1 and v2 < v1:
            picked_better_counts += 1
    if diff_counts == 0:
        return 1e10
    else:
        q_val = picked_better_counts/diff_counts
        w = max(1e-4,q_val + c*np.sqrt(math.log(len(filtered))/diff_counts))
    return w
