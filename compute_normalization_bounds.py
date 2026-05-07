import pandas as pd
import json
import time
import math
import os
import cpmpy as cp
from cpmpy import SolverLookup
from utils.jobshop_model_final import FJTransportProblemFinal

def solve_for_objective(json_file, target_obj, sense='min', timeout=300):
    """
    Solves the problem for a single objective and returns all objective values.
    """
    problem = FJTransportProblemFinal(custom_bound=True, json_file=json_file, symmetry_breaking=True)
    problem.make_model()
    
    model = problem.model
    obj_expr = problem.objectives[target_obj]
    
    if sense == 'min':
        model.minimize(obj_expr)
    else:
        model.maximize(obj_expr)
    
    solver = SolverLookup.get('ortools', model)
    start_time = time.time()
    solver_status = solver.solve(time_limit=timeout)
    elapsed = time.time() - start_time
    
    if solver_status:
        objectives_names = ['makespan', 'workstations', 'employees', 'robots', 'employee_time']
        objs = {
            name: (
                (1 / 3600) * float(problem.objectives[name].value())
                if name in {"makespan", "employee_time"}
                else float(problem.objectives[name].value())
            )
            for name in objectives_names
        }
        return True, objs, elapsed
    return False, None, elapsed

def compute_normalization_bounds(json_file, timeout=300):
    """
    Computes optimal and nadir points by optimizing each objective individually.
    """
    objectives_names = ['makespan', 'workstations', 'employees', 'robots', 'employee_time']
    all_objs_collected = []

    for obj_name in objectives_names:
        # Minimize each objective
        print(f"  Minimizing {obj_name} (timeout={timeout}s)...")
        status, objs, elapsed = solve_for_objective(json_file, obj_name, sense='min', timeout=timeout)
        if status:
            print(f"    Result for {obj_name}: {objs[obj_name]} in {elapsed:.2f}s")
            all_objs_collected.append(objs)
        else:
            print(f"    Failed to minimize {obj_name}")

        # Maximize each objective
        print(f"  Maximizing {obj_name} (timeout={timeout}s)...")
        status, objs, elapsed = solve_for_objective(json_file, obj_name, sense='max', timeout=timeout)
        if status:
            print(f"    Result for {obj_name}: {objs[obj_name]} in {elapsed:.2f}s")
            all_objs_collected.append(objs)
        else:
            print(f"    Failed to maximize {obj_name}")

    if not all_objs_collected:
        return None, None

    df = pd.DataFrame(all_objs_collected)
    optimal_point = df.min()
    nadir_point = df.max()
    
    return optimal_point, nadir_point

def main():
    # Process the datasets used in solve_with_preferences
    datasets = ['data/data_training_2.json']
    os.makedirs('data/normalization', exist_ok=True)
    
    for json_path in datasets:
        if not os.path.exists(json_path):
            print(f"Skipping {json_path}: File not found.")
            continue
            
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        print(f"\nProcessing {json_path}...")
        
        optimal, nadir = compute_normalization_bounds(json_path, timeout=300)
        
        if optimal is not None:
            optimal_df = optimal.to_frame().T
            nadir_df = nadir.to_frame().T
            
            opt_file = f'data/normalization/{base_name}_optimal_values.csv'
            nad_file = f'data/normalization/{base_name}_nadir_maximization.csv'
            
            optimal_df.to_csv(opt_file, index=False)
            nadir_df.to_csv(nad_file, index=False)
            
            print(f"  Saved bounds to:")
            print(f"    - {opt_file}")
            print(f"    - {nad_file}")
        else:
            print(f"  Failed to compute bounds for {json_path}")

if __name__ == "__main__":
    main()
