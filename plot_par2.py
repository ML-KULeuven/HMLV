import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
import seaborn as sns

timeout = 600
RESULT_PATTERNS = [
    "cp_model_results/**/solution_data_training_1_*.csv",
    "data/cp_model_results/**/solution_data_training_1_*.csv",
]

# Mapping training instance number to total items
items_map = {
    '1': 4,
    '2': 8,
    '3': 12,
    '4': 16,
    '5': 20
}

def compute_par2(df):
    par2_values = []
    for _, row in df.iterrows():
        status = str(row['status'])
        time = float(row['elapsed'])
        
        if time >= timeout or ('OPTIMAL' not in status and 'FEASIBLE' not in status):
            par2_values.append(2 * timeout)
        else:
            par2_values.append(time)
            
    return sum(par2_values) / len(par2_values) if par2_values else 0

def infer_solver_and_constraint(path):
    parts = os.path.normpath(path).split(os.sep)

    if parts[:2] == ["data", "cp_model_results"]:
        solver_index = 2
    elif parts[:1] == ["cp_model_results"]:
        solver_index = 1
    else:
        return None, None

    if len(parts) <= solver_index:
        return None, None

    solver = parts[solver_index]

    # Preferred layout: <root>/<solver>/<formulation>/solution_*.csv
    if len(parts) > solver_index + 2:
        return solver, parts[solver_index + 1]

    # Fallback for flat outputs written directly under <root>/<solver>/.
    filename = parts[-1].lower()
    if "nooverlapoptional" in filename:
        return solver, "nooverlapOptional"
    if "cumulativeoptional" in filename:
        return solver, "cumulativeOptional"
    if "nooverlap" in filename:
        return solver, "nooverlap"
    if "cumulative" in filename:
        return solver, "cumulative"

    return solver, "unknown"

results = []
files = sorted({
    f
    for pattern in RESULT_PATTERNS
    for f in glob.glob(pattern, recursive=True)
})

for f in files:
    solver, constraint = infer_solver_and_constraint(f)
    if solver is None or constraint is None:
        continue

    filename = os.path.basename(f)
    
    try:
        name_parts = filename.split('_')
        num = name_parts[4]
        items = items_map.get(num)
        
        if items is None: continue
        
        df = pd.read_csv(f)
        avg_par2 = compute_par2(df)
        
        results.append({
            'solver': solver,
            'constraint': constraint,
            'no_of_items': items,
            'avg_par2': avg_par2
        })
    except Exception as e:
        print(f"Error processing {f}: {e}")

df_results = pd.DataFrame(results)

if not df_results.empty:
    sns.set_theme(style="whitegrid")

    # Apply style from plot_custom.py
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Color palette chosen with different luminance, plus redundant
    # markers/dashes so the lines remain distinct in grayscale.
    palette = {"gurobi": "#004488", "ortools": "#E69F00"}
    markers = {
        "cumulative": "o",
        "cumulativeOptional": "^",
        "nooverlap": "s",
        "nooverlapOptional": "D",
    }
    dashes = {
        "cumulative": "",
        "cumulativeOptional": (1, 1),
        "nooverlap": (4, 2),
        "nooverlapOptional": (6, 2, 1, 2),
    }
    
    sns.lineplot(data=df_results.sort_values('no_of_items'), 
                 x='no_of_items', y='avg_par2', 
                 hue='solver', style='constraint',
                 palette=palette,
                 markers=markers, dashes=dashes, ax=ax,
                 linewidth=3.5, markersize=14)

    for line in ax.lines:
        line.set_markeredgecolor("#111111")
        line.set_markeredgewidth(1.2)
    
    # Updated Labels
    ax.set_ylabel('PAR2 Score (s)', fontsize=24, fontweight='bold')
    ax.set_xlabel('No. of Items', fontsize=24, labelpad=15, fontweight='bold')
    
    # Tick labels
    ax.set_xticks([4, 8, 12, 16, 20])
    ax.set_xlim(left=3.5) # Start a bit before 4
    ax.tick_params(axis='x', labelsize=22)
    ax.tick_params(axis='y', labelsize=20)
    
    # Clean Legend: Reorder and rename labels
    handles, labels = ax.get_legend_handles_labels()
    mapping = {
        'gurobi': 'Gurobi',
        'ortools': 'Ortools',
        'cumulative': 'Cumulative',
        'cumulativeOptional': 'CumulativeOptional',
        'nooverlap': 'NoOverlap',
        'nooverlapOptional': 'NoOverlapOptional'
    }
    desired_order = [
        'Gurobi',
        'Ortools',
        'Cumulative',
        'CumulativeOptional',
        'NoOverlap',
        'NoOverlapOptional',
    ]
    
    label_to_handle = {mapping[l]: h for h, l in zip(handles, labels) if l in mapping}
    filtered_handles = [label_to_handle[l] for l in desired_order if l in label_to_handle]
    filtered_labels = [l for l in desired_order if l in label_to_handle]
    
    ax.legend(filtered_handles, filtered_labels, fontsize=16, frameon=True, loc='best')
    
    # Grid: Only horizontal lines, remove vertical lines
    ax.grid(True, axis='y', alpha=0.25)
    ax.grid(False, axis='x')
    
    plt.tight_layout()
    
    output_path = 'results/RQ11.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"Plot saved to {output_path}")
else:
    print("No data found.")
