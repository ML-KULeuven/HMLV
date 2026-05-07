import pandas as pd
import glob
import os
import numpy as np

def compute_stats(directories, max_queries=20):
    for root_dir in directories:
        if not os.path.exists(root_dir):
            print(f"\nWarning: Directory {root_dir} not found.")
            continue
        
        summed_times_first_two = []
        found_files = []
        
        # Find all dataset.csv files recursively
        files = glob.glob(os.path.join(root_dir, '**', 'dataset.csv'), recursive=True)
        for f in files:
            # APPLY FILTERS: norm_custom, div_UCB, dis_True
            if 'norm_custom' in f and 'div_UCB' in f and 'dis_True' in f:
                try:
                    df = pd.read_csv(f)
                    
                    # For the sum of the first two queries (iter 1 and iter 2)
                    # We need to sum 'time 1' and 'time 2' for iter 1, and for iter 2.
                    # Actually, usually "first two queries" in this context refers to the first two rows (iter 1 and 2).
                    # Each row represents a query with two solutions compared (time 1 and time 2).
                    
                    df_first_two = df[df['iter'].isin([1, 2])]
                    
                    if not df_first_two.empty:
                        # Sum all solve times for iter 1 and iter 2
                        # Each iter has time 1 and time 2
                        total_time = df_first_two[['time 1', 'time 2']].sum().sum()
                        summed_times_first_two.append(total_time)
                        found_files.append(f)
                        
                except Exception as e:
                    print(f"Error reading {f}: {e}")

        print(f"\nProcessing {root_dir}...")
        if summed_times_first_two:
            avg_summed_time = np.mean(summed_times_first_two)
            std_summed_time = np.std(summed_times_first_two)
            print(f"Analysis of first 2 queries SUMMED (iter 1 + iter 2) across {len(found_files)} user configurations:")
            print(f"Filters: norm_custom, div_UCB, dis_True")
            print(f"------------------------------------------------------------------")
            print(f"Average summed solve time: {avg_summed_time:.4f} seconds")
            print(f"Standard deviation: {std_summed_time:.4f} seconds")
        else:
            print("No data found matching the filters.")

if __name__ == "__main__":
    target_dirs = ['results_CPE_lex_1', 'results_CPE_lex_2']
    compute_stats(target_dirs)
