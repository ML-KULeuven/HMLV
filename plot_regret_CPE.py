import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def format_sci_compact(x):
    # Use .1e to get the standard scientific notation
    s = f"{x:.1e}"
    mantissa, exp = s.split("e")
    exp_int = int(exp)
    
    # Special case for the user's request: if it's around 6e-3, round the mantissa to integer
    if exp_int == -3:
        mantissa = str(int(round(float(mantissa))))
    
    if mantissa.endswith(".0"):
        mantissa = mantissa[:-2]
    exp = str(exp_int)
    return f"{mantissa}e{exp}"


def parse_method(method):
    norm_match = re.search(r"norm_([^/]+)", method)
    div_match = re.search(r"div_([^/]+)", method)
    dis_match = re.search(r"dis_(True|False)", method)

    normalization = norm_match.group(1) if norm_match else "unknown"
    div = div_match.group(1) if div_match else "unknown"
    dis = dis_match.group(1) if dis_match else "unknown"

    if div == "base" and dis == "False":
        variant = "ChoPerc"
    elif div == "base" and dis == "True":
        variant = "ChoPerc with Disjunction"
    else:
        variant = "MACHOP"

    return normalization, variant


def make_plot(input_csv, output_png):
    df = pd.read_csv(input_csv)
    if df.empty:
        raise ValueError(f"No rows found in {input_csv}")

    filename = os.path.basename(input_csv).lower()
    is_lex = "lex" in filename and "simplex" not in filename
    y_max = 1.6 if is_lex else 0.5
    title_type = "Lexicographic Order" if is_lex else "Weighted"

    required_cols = {"Method", "Queries", "AvgRegret", "StdRegret"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Ensure Queries are numeric
    df["Queries"] = pd.to_numeric(df["Queries"])
    
    # Process method names
    parsed = df["Method"].apply(parse_method)
    df["Normalization"] = parsed.apply(lambda x: x[0])
    df["Variant"] = parsed.apply(lambda x: x[1])

    # Expected bar order for each normalization group.
    variant_order = ["ChoPerc", "ChoPerc with Disjunction", "MACHOP"]
    norm_preferred = ["base", "local", "custom"]
    norm_label_map = {
        "base": "Default",
        "local": "Update - Local",
        "custom": "SNOW",
    }
    
    unique_norms = df["Normalization"].unique()
    normalizations = [n for n in norm_preferred if n in unique_norms]
    normalizations += sorted([n for n in unique_norms if n not in normalizations])

    query_targets = [20, 40, 60]
    fig, axes = plt.subplots(len(query_targets), 1, figsize=(11, 14), sharex=True)
    # Different luminance levels keep the bars distinguishable in grayscale.
    colors = ["#004488", "#D55E00", "#F0E442"]
    width = 0.24
    x = np.arange(len(normalizations))

    for idx, q_target in enumerate(query_targets):
        ax = axes[idx]
        q_df = df[df["Queries"] == q_target]
        
        avg_pivot = (
            q_df.pivot_table(
                index="Normalization",
                columns="Variant",
                values="AvgRegret",
                aggfunc="first",
            )
            .reindex(index=normalizations)
            .reindex(columns=variant_order)
        )
        std_pivot = (
            q_df.pivot_table(
                index="Normalization",
                columns="Variant",
                values="StdRegret",
                aggfunc="first",
            )
            .reindex(index=normalizations)
            .reindex(columns=variant_order)
        )

        for i, variant in enumerate(variant_order):
            if variant not in avg_pivot.columns:
                continue
            vals = avg_pivot[variant].to_numpy(dtype=float)
            std_vals = std_pivot[variant].to_numpy(dtype=float)
            
            bars = ax.bar(
                x + (i - 1) * width,
                vals,
                yerr=std_vals,
                capsize=5,
                width=width,
                label=variant if idx == 0 else "", # Only label first subplot
                color=colors[i],
                edgecolor="black",
                linewidth=1.5,
            )
            
            for bar, mu in zip(bars, vals):
                if np.isnan(mu):
                    continue
                mu_txt = f"{mu:.2f}" if abs(mu) >= 0.01 else format_sci_compact(mu)
                # Position text slightly higher to avoid error bars
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01,
                    mu_txt,
                    ha="center",
                    va="bottom",
                    fontsize=14,
                    fontweight="bold",
                )

        ax.set_ylabel("Average regret", fontsize=22, fontweight="bold")
        ax.set_title(f"{title_type} - Regret ({q_target} queries)", fontsize=20, fontweight="bold")
        ax.set_ylim(0, y_max)
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis='y', labelsize=18)
        if idx == 0:
            ax.legend(fontsize=18, loc="upper right")

    plt.xticks(x, [norm_label_map.get(n, n) for n in normalizations], fontsize=20)
    axes[-1].set_xlabel("Normalization", fontsize=22, labelpad=15, fontweight="bold")
    
    plt.suptitle(f"{title_type} - Regret", fontsize=24, fontweight="bold")
    
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(output_png, dpi=300)
    plt.close(fig)


def make_individual_plots(input_csv, output_prefix):
    df = pd.read_csv(input_csv)
    if df.empty:
        raise ValueError(f"No rows found in {input_csv}")

    filename = os.path.basename(input_csv).lower()
    is_lex = "lex" in filename and "simplex" not in filename
    y_max = 1.6 if is_lex else 0.5
    title_type = "Lexicographic Order" if is_lex else "Weighted"

    df["Queries"] = pd.to_numeric(df["Queries"])
    parsed = df["Method"].apply(parse_method)
    df["Normalization"] = parsed.apply(lambda x: x[0])
    df["Variant"] = parsed.apply(lambda x: x[1])

    variant_order = ["ChoPerc", "ChoPerc with Disjunction", "MACHOP"]
    norm_preferred = ["base", "local", "custom"]
    norm_label_map = {"base": "Default", "local": "Update - Local", "custom": "SNOW"}
    
    unique_norms = df["Normalization"].unique()
    normalizations = [n for n in norm_preferred if n in unique_norms]
    normalizations += sorted([n for n in unique_norms if n not in normalizations])

    query_targets = [20, 40, 60]
    # Different luminance levels keep the bars distinguishable in grayscale.
    colors = ["#004488", "#D55E00", "#F0E442"]
    width = 0.24
    x = np.arange(len(normalizations))

    for q_target in query_targets:
        fig, ax = plt.subplots(figsize=(10, 7))
        q_df = df[df["Queries"] == q_target]
        
        avg_pivot = (
            q_df.pivot_table(index="Normalization", columns="Variant", values="AvgRegret", aggfunc="first")
            .reindex(index=normalizations)
            .reindex(columns=variant_order)
        )
        std_pivot = (
            q_df.pivot_table(index="Normalization", columns="Variant", values="StdRegret", aggfunc="first")
            .reindex(index=normalizations)
            .reindex(columns=variant_order)
        )

        for i, variant in enumerate(variant_order):
            if variant not in avg_pivot.columns:
                continue
            vals = avg_pivot[variant].to_numpy(dtype=float)
            std_vals = std_pivot[variant].to_numpy(dtype=float)
            
            bars = ax.bar(x + (i - 1) * width, vals, yerr=std_vals, capsize=6, width=width, label=variant, color=colors[i], edgecolor="black", linewidth=1.5)
            
            for bar, mu in zip(bars, vals):
                if np.isnan(mu): continue
                mu_txt = f"{mu:.2f}" if abs(mu) >= 0.01 else format_sci_compact(mu)
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, mu_txt, ha="center", va="bottom", fontsize=16, fontweight="bold")

        ax.set_ylabel("Average regret", fontsize=24, fontweight="bold")
        ax.set_xlabel("Normalization", fontsize=24, fontweight="bold")
        ax.set_title(f"{title_type} - Regret ({q_target} queries)", fontsize=26, fontweight="bold")
        ax.set_ylim(0, y_max)
        ax.set_xticks(x)
        ax.set_xticklabels([norm_label_map.get(n, n) for n in normalizations], fontsize=22)
        ax.tick_params(axis='y', labelsize=20)
        ax.legend(fontsize=20)
        ax.grid(axis="y", alpha=0.25)
        
        output_path = f"{output_prefix}_{q_target}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.tight_layout()
        fig.savefig(output_path, dpi=300)
        plt.close(fig)
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot grouped bars from results.csv")
    parser.add_argument("--input", default="results/lex_cpe.csv", help="Input CSV path")
    parser.add_argument("--output", default="results/tuning_comparison.png", help="Output image path for combined plot")
    parser.add_argument("--individual", action="store_true", help="Also generate individual plots for each query threshold")
    args = parser.parse_args()

    make_plot(args.input, args.output)
    print(f"Saved: {args.output}")
    
    if args.individual:
        prefix = args.output.replace(".png", "")
        make_individual_plots(args.input, prefix)
