import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def format_sci_compact(x):
    if x == 0:
        return "0"
    s = f"{x:.1e}"
    mantissa, exp = s.split("e")
    if mantissa.endswith(".0"):
        mantissa = mantissa[:-2]
    exp = str(int(exp))
    return f"{mantissa}e{exp}"

def get_data(file_path, method, queries):
    df = pd.read_csv(file_path)
    row = df[(df['Method'] == method) & (df['Queries'] == queries)]
    if row.empty:
        print(f"Warning: No data found for {method} at {queries} queries in {file_path}")
        return 0, 0
    return row['AvgRegret'].values[0], row['StdRegret'].values[0]

# Data retrieval
lex_machop_avg, lex_machop_std = get_data('results/lex_cpe.csv', 'norm_custom/div_UCB/dis_True', 20.0)
lex_dws_avg, lex_dws_std = get_data(F'results/lex_dws.csv', 'norm_base', 20.0)

uni_machop_avg, uni_machop_std = get_data('results/w_cpe.csv', 'norm_custom/div_UCB/dis_True', 20.0)
uni_dws_avg, uni_dws_std = get_data('results/w_dws.csv', 'norm_base', 20.0)

# Labels and grouping
labels = ['Lexicographic Order', 'Weighted']
dws_avgs = [lex_dws_avg, uni_dws_avg]
dws_stds = [lex_dws_std, uni_dws_std]
machop_avgs = [lex_machop_avg, uni_machop_avg]
machop_stds = [lex_machop_std, uni_machop_std]

x = np.arange(len(labels))
width = 0.3  # bar width
# Reuse the grayscale-safe palette from plot_par2.py.
colors = ["#004488", "#E69F00"]

fig, ax = plt.subplots(figsize=(10, 7))

# Plot bars
rects1 = ax.bar(x - width/2, dws_avgs, width, yerr=dws_stds, capsize=4, 
                label='DWS', color=colors[0], edgecolor='black', linewidth=1.0)
rects2 = ax.bar(x + width/2, machop_avgs, width, yerr=machop_stds, capsize=4, 
                label='MACHOP', color=colors[1], edgecolor='black', linewidth=1.0)

# Add text on top of bars
for rects in [rects1, rects2]:
    for rect in rects:
        height = rect.get_height()
        if np.isnan(height): continue
        txt = f"{height:.2f}" if abs(height) >= 0.01 else format_sci_compact(height)
        ax.text(rect.get_x() + rect.get_width()/2., height + 0.01,
                txt, ha='center', va='bottom', fontsize=16, fontweight='bold')

# Styling
ax.set_ylabel('Average regret', fontsize=24, fontweight='bold')
ax.set_title('Regret (20 Queries)', fontsize=26, fontweight='bold', pad=10)
ax.set_xlabel('Preference Types', fontsize=24, labelpad=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=22)
ax.tick_params(axis='y', labelsize=20)
ax.legend(fontsize=20)
ax.grid(axis='y', alpha=0.25)

# Setting y-axis limit to accommodate error bars and text
max_val = max(max([m+s for m,s in zip(machop_avgs, machop_stds)]), 
              max([d+s for d,s in zip(dws_avgs, dws_stds)]))
ax.set_ylim(0, max_val * 1.1)

fig.tight_layout()

output_path = 'results/DWS_CPE.png'
plt.savefig(output_path, dpi=300)
plt.close(fig)
print(f"Plot saved to {output_path}")
