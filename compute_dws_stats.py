import os
import pandas as pd
import glob
import numpy as np

def process_dirs(results_dirs):
    if isinstance(results_dirs, str):
        results_dirs = [results_dirs]
        
    all_times_per_20_queries = []
    all_solve_calls_per_20_queries = []
    
    for results_dir in results_dirs:
        pattern = os.path.join(results_dir, "user_*", "norm_base", "**", "solve_history.csv")
        files = glob.glob(pattern, recursive=True)
        
        for f in files:
            try:
                df = pd.read_csv(f)
                df_20 = df[df['iter'] <= 20]
                
                # 1. Average Time per query
                total_time_20 = df_20['solve_time'].sum()
                all_times_per_20_queries.append(total_time_20 / 20.0)
                
                # 2. Average Solve Calls per query
                total_calls_20 = len(df_20)
                all_solve_calls_per_20_queries.append(total_calls_20 / 20.0)
                
            except Exception as e:
                pass
                
    if all_times_per_20_queries:
        print(f"--- Aggregated: {', '.join(results_dirs)} ---")
        print(f"Average time per query: {np.mean(all_times_per_20_queries):.4f} s (std: {np.std(all_times_per_20_queries):.4f} s)")
        print(f"Average solve calls per query: {np.mean(all_solve_calls_per_20_queries):.4f} (std: {np.std(all_solve_calls_per_20_queries):.4f})")
        print()

def process_cpe_dirs(results_dirs):
    if isinstance(results_dirs, str):
        results_dirs = [results_dirs]
        
    all_times_per_20_queries = []
    all_solve_calls_per_20_queries = []
    
    for results_dir in results_dirs:
        # Update pattern to use norm_custom and div_UCB
        pattern = os.path.join(results_dir, "user_*", "norm_custom", "div_UCB", "**", "dataset.csv")
        files = glob.glob(pattern, recursive=True)
        
        for f in files:
            try:
                df = pd.read_csv(f)
                df_20 = df[df['iter'] <= 20]
                
                # 1. Average Time per query
                total_time_20 = (df_20['time 1'] + df_20['time 2']).sum()
                all_times_per_20_queries.append(total_time_20 / 20.0)
                
                # 2. Average Solve Calls per query
                total_calls_20 = len(df_20) * 2
                all_solve_calls_per_20_queries.append(total_calls_20 / 20.0)
                
            except Exception as e:
                pass
                
    if all_times_per_20_queries:
        print(f"--- Aggregated CPE (norm_custom, div_UCB): {', '.join(results_dirs)} ---")
        print(f"Average time per query: {np.mean(all_times_per_20_queries):.4f} s (std: {np.std(all_times_per_20_queries):.4f} s)")
        print(f"Average solve calls per query: {np.mean(all_solve_calls_per_20_queries):.4f} (std: {np.std(all_solve_calls_per_20_queries):.4f})")
        print()

if __name__ == "__main__":
    print("DWS Stats:")
    process_dirs(["results_DWS_1", "results_DWS_2"])
    
    print("\nCPE Stats:")
    process_cpe_dirs(["results_CPE_W_1", "results_CPE_W_2"])
