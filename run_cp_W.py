
import argparse
import pandas as pd
import os

from utils.CPE import CPE
from utils.utility_classes import Oracle
from utils.jobshop_model_final import FJTransportProblemFinal


def main():
    parser = argparse.ArgumentParser(description="Hyperparameter tuning for CPE.")
    parser.add_argument("-n","--normalization", type=str, choices=['base','local','custom'], default='base',
                        help="Normalization method: 'base' or 'custom'.")
    parser.add_argument("-d","--diversification", type=str, choices=['base', 'UCB'], default='base',
                        help="Diversification method: 'base', or 'UCB'.")
    parser.add_argument("-c","--disjunctive", type=lambda x: str(x).lower() == 'true', default=True,
                        help="Whether to use disjunctive constraints (True/False).")
    parser.add_argument("-t", "--training", type=int, choices=[1, 2, 3], default=1,
                        help="Training data index (1, 2, or 3).")
    args = parser.parse_args()


    for user_index in [30,31,32,33,34,35,36,37,38,39]: # Loop over user indices for tuning
        # --- Search space ---
        objectives = ['makespan', 'workstations', 'employees', 'robots', 'employee_time']

        # --- Read user preferences ---
        try:
            user_prefs_df = pd.read_csv('data/user_preferences.csv')
            user_weights_series = user_prefs_df.iloc[user_index]
            # Map preference columns to objective names
            user_weights = {obj: user_weights_series[obj] for obj in objectives}
        except (FileNotFoundError, IndexError):
            print(f"Error: Could not read user preferences for index {user_index}.")
            print("Please ensure 'data/user_preferences.csv' exists and the index is valid.")
            continue

        # --- Read preferred solution from appropriate solution file ---
        # Map training index to solution file
        if args.training == 1:
            solution_file = 'data/solution_training_1.csv'
        elif args.training == 2:
            solution_file = 'data/solution_training_2.csv'
        else: # args.training == 3
            solution_file = 'data/solution_training_3.csv'

        
        try:
            solution_training_df = pd.read_csv(solution_file)
            # Assuming each row in solution_training_df corresponds to a user_index
            # and 'objectives' column contains the preferred solution as a string dictionary
            preferred_solution_str = solution_training_df.iloc[user_index]['objectives']
            import ast
            preferred_solution = ast.literal_eval(preferred_solution_str)
        except (FileNotFoundError, IndexError, ValueError) as e:
            print(f"Error: Could not read preferred solution for index {user_index} from '{solution_file}'.")
            print(f"Details: {e}")
            continue

        # --- Instantiate Model (once) ---
        json_file = f'data/data_training_{args.training}.json'
        print(f"Initializing the Job Shop model with {json_file}...")
        model = FJTransportProblemFinal(
            json_file=json_file, symmetry_breaking=False
        )
        model.make_model()
        print("Model initialized.")

        # --- Main tuning loop ---
        results_root = F'results_CPE_W_{args.training}'

        # --- Determine Nadir filepath based on normalization argument ---
        nadir_method_name = args.normalization # Renaming for clarity in output paths
        nadir_filepath = f'data/normalization/data_training_{args.training}_nadir_maximization.csv'
        optimal_filepath = f'data/normalization/data_training_{args.training}_optimal_values.csv'


        print(f"===== Starting Tuning for Normalization Method: {nadir_method_name} (Training {args.training}) =====")

        # --- Load Nadir and Optimal Points for the current method ---
        print(f"Loading nadir values from {nadir_filepath}...")
        try:
            optimal_df = pd.read_csv(optimal_filepath)
            nadir_df = pd.read_csv(nadir_filepath)
        except FileNotFoundError:
            print(f"Error: Normalization files for training {args.training} not found.")
            print(f"Please run compute_normalization_bounds.py first.")
            continue

        nadir_optimal_results_data = {}
        for obj_name in objectives:
            if obj_name in optimal_df.columns and obj_name in nadir_df.columns:
                nadir_optimal_results_data[obj_name] = {
                    'min': optimal_df[obj_name].iloc[0],
                    'max': nadir_df[obj_name].iloc[0]
                }
            else:
                raise ValueError(f"Objective '{obj_name}' not found in optimal or nadir data.")
        print("Nadir and optimal values loaded successfully.")

        hyperparameter_norm_div_dis = {
            'base': {
                'base': {
                    'False' : [1, 2],
                    'True': [1, 2]
                },
                'UCB': {
                    'True': [1,4]
                }
            },
            'local': {
                'base': {
                    'False': [10, 2],
                    'True': [10, 2]
                },
                'UCB': {
                    'True': [10,3]
                }
            },
            'custom': {
                'base': {
                    'False': [1, 2],
                    'True': [10, 2]
                },
                'UCB': {
                    'True': [1,2]
                }
            }
        }

        # Use args.disjunctive directly, no inner loop
        disjunctive = args.disjunctive
        lr = hyperparameter_norm_div_dis[args.normalization][args.diversification][str(disjunctive)][0]
        c_val = hyperparameter_norm_div_dis[args.normalization][args.diversification][str(disjunctive)][1]

        print(f"--- Running for lr={lr}, disjunctive={disjunctive}, normalization={args.normalization}, diversification={args.diversification}, c_ucb={c_val} ---")

        # --- Setup for the run ---
        output_dir_parts = [results_root, f'user_{user_index}', f'norm_{args.normalization}', f'div_{args.diversification}']
        if args.diversification == 'UCB':
            output_dir_parts.append(f'c_{c_val}') # Add c_val to path for UCB
        output_dir_parts.extend([f'lr_{lr}', f'dis_{disjunctive}'])
        output_dir = os.path.join(*output_dir_parts)
        os.makedirs(output_dir, exist_ok=True)

        # --- Instantiate Oracle ---
        lbda_indif = 1 if user_index > 20 else 0.001
        oracle = Oracle(weights=list(user_weights.values()), objectives=objectives, lbda_indif=lbda_indif)

        # --- Instantiate and run CPE ---
        cpe = CPE(
            model=model,
            oracle=oracle,
            objectives=objectives,
            preferred=preferred_solution, # Passing the preferred solution
            nadir_optimal_results=nadir_optimal_results_data,
            output_location=output_dir,
            lr=lr,
            disjunctive=disjunctive,
            normalization=args.normalization, # Pass the argparse value
            diversification=args.diversification, # Pass the argparse value
            c_ucb=c_val, # Pass the 'c' hyperparameter for UCB from the loop
            max_data=80, # Using a reasonable default for tuning
            time_eval=20
        )

        print(f"Starting CPE process for user {user_index}. Results will be saved in {output_dir}")
        try:
            cpe.start()
            print(f"CPE process finished for user {user_index}.")
        except Exception as e:
            error_msg = f"CPE failed for user {user_index} with parameters: lr={lr}, disjunctive={disjunctive}, normalization={args.normalization}, diversification={args.diversification}, c_ucb={c_val}, training={args.training}. Error: {e}\n"
            print(f"Error: {error_msg}")
            with open("cpe_failures.log", "a") as f:
                f.write(error_msg)
            continue

        print("Hyperparameter tuning complete for all specified parameters.")

if __name__ == "__main__":
    main()
