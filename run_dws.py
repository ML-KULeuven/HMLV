import argparse
import pandas as pd
import os
import ast

from utils.DWS import DWS
from utils.utility_classes import Oracle
from utils.jobshop_model_final import FJTransportProblemFinal


def main():
    parser = argparse.ArgumentParser(description="Run DWS with best hyperparameters.")
    parser.add_argument("-n", "--normalization", type=str, choices=['base', 'custom'],
                        default='base', help="Type of normalization to use: 'base' or 'custom'")
    args = parser.parse_args()

    normalization_type = args.normalization

    # Best hyperparameters found from tuning
    best_hyperparams = {
        'base': {'lb': 2, 'alpha': 1},
        'custom': {'lb': 1.5, 'alpha': 10}
    }
    
    lb = best_hyperparams[normalization_type]['lb']
    alpha = best_hyperparams[normalization_type]['alpha']
    
    objectives = ['makespan', 'workstations', 'employees', 'robots', 'employee_time']

    # --- Instantiate Model (once) ---
    print("Initializing the Job Shop model...")
    model = FJTransportProblemFinal(
        json_file='data/data_training_2.json'
    )
    model.make_model()
    print("Model initialized.")

    results_root = 'results_DWS_2'
    nadir_filepath = 'data/normalization/data_training_2_nadir_maximization.csv'

    # Loop over users 5 to 14 as in run_cp.py
    for user_index in [5,6,7,8,9,10,11,12,13,14]:
        print(f"===== Processing User {user_index} for Normalization: {normalization_type} =====")

        # --- Read user preferences ---
        try:
            user_prefs_df = pd.read_csv('data/user_preferences.csv')
            user_weights_series = user_prefs_df.iloc[user_index]
            user_weights = {obj: user_weights_series[obj] for obj in objectives}
        except (FileNotFoundError, IndexError):
            print(f"Error: Could not read user preferences for index {user_index}.")
            continue

        # --- Read preferred solution from solution_training.csv ---
        try:
            solution_training_df = pd.read_csv('data/solution_training_2.csv')
            preferred_solution_str = solution_training_df.iloc[user_index]['objectives']
            preferred_solution = ast.literal_eval(preferred_solution_str)
        except (FileNotFoundError, IndexError, ValueError) as e:
            print(f"Error: Could not read preferred solution for index {user_index}. Details: {e}")
            continue

        # --- Load Nadir and Optimal Points ---
        optimal_df = pd.read_csv('data/normalization/data_training_2_optimal_values.csv')
        nadir_df = pd.read_csv(nadir_filepath)

        nadir_optimal_results_data = {}
        for obj_name in objectives:
            nadir_optimal_results_data[obj_name] = {
                'min': optimal_df[obj_name].iloc[0],
                'max': nadir_df[obj_name].iloc[0]
            }

        # --- Instantiate Oracle ---
        lbda_indif = 1 if user_index >= 20 else 0.001
        optimal_sol = {obj: optimal_df[obj].iloc[0] for obj in objectives if obj in optimal_df.columns}
        oracle = Oracle(weights=list(user_weights.values()), objectives=objectives, optimal_sol=optimal_sol,
                        lbda_indif=lbda_indif)

        output_dir = os.path.join(results_root, f'user_{user_index}', f'norm_{normalization_type}', f'lb_{lb}', f'alpha_{alpha}')
        os.makedirs(output_dir, exist_ok=True)

        print(f"--- Running DWS for lb={lb}, ub={alpha}, norm={normalization_type} ---")
        
        dws = DWS(
            model=model,
            oracle=oracle,
            objectives=objectives,
            preferred=preferred_solution,
            nadir_optimal_results=nadir_optimal_results_data,
            output_location=output_dir,
            normalization=normalization_type,
            lb=lb,
            alpha=alpha,
            max_data=60,
            time_eval=20
        )

        dws.start()
        print(f"DWS process for user {user_index} finished. Results in {output_dir}")

    print("All DWS runs complete.")

if __name__ == "__main__":
    main()
