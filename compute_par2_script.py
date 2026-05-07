import pandas as pd
import glob
import os

timeout = 600

def compute_par2(df):
    par2_values = []
    for _, row in df.iterrows():
        status = str(row['status'])
        time = float(row['elapsed'])
        
        # Determine if it's a success
        # Typically OPTIMAL or FEASIBLE are successes.
        # LIMIT_REACHED or similar might be failures if no solution found,
        # but usually PAR2 uses time * 2 for timeouts.
        
        # If time is close to or greater than timeout, or status indicates failure
        if time >= timeout or "OPTIMAL" not in status and "FEASIBLE" not in status:
            par2_values.append(2 * timeout)
        else:
            par2_values.append(time)
            
    return sum(par2_values) / len(par2_values) if par2_values else 0

results = []

# Pattern for solution_data_training_1_{number}
files = glob.glob("data/cp_model_results/**/solution_data_training_1_*.csv", recursive=True)

for f in files:
    # Path is data/cp_model_results/{solver}/{constraint_type}/solution_data_training_1_{number}_{...}.csv
    parts = f.split(os.sep)
    # Depending on where the file is, parts might vary.
    # data/cp_model_results/gurobi/cumulative/solution_data_training_1_1_gurobi_sym_lb_cumulative.csv
    # parts: ['data', 'cp_model_results', 'gurobi', 'cumulative', '...']
    
    solver = parts[2]
    constraint = parts[3]
    filename = parts[-1]
    
    # Extract number from filename
    # solution_data_training_1_1_gurobi_sym_lb_cumulative.csv
    num = filename.split('_')[4]
    
    try:
        df = pd.read_csv(f)
        avg_par2 = compute_par2(df)
        results.append({
            'solver': solver,
            'constraint': constraint,
            'number': num,
            'avg_par2': avg_par2,
            'file': filename
        })
    except Exception as e:
        print(f"Error processing {f}: {e}")

df_results = pd.DataFrame(results)
print(df_results.sort_values(['solver', 'constraint', 'number']).to_string(index=False))
