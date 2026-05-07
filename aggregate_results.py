import argparse
import os
import re
from pathlib import Path

import pandas as pd


HP_PREFIXES = ["c", "lr", "lb", "ub", "n", "alpha"]
TARGET_QUERIES = [20, 60, 80]


def parse_hp(hp_string, param):
    match = re.search(fr"{param}_([^, ]+)", hp_string)
    return match.group(1) if match else None


def aggregate_regret(root_dirs):
    if isinstance(root_dirs, str):
        root_dirs = [root_dirs]
    all_data = []

    for root_dir in root_dirs:
        root_path = Path(root_dir)
        for regret_file in root_path.glob("**/regret.csv"):
            parts = regret_file.relative_to(root_path).parts
            user = f"{root_dir}_{parts[0]}"

            method_parts = []
            hp_parts = []
            for part in parts[1:-1]:
                if any(part.startswith(prefix + "_") for prefix in HP_PREFIXES):
                    hp_parts.append(part)
                else:
                    method_parts.append(part)

            method = "/".join(method_parts)
            hyperparams = ", ".join(hp_parts)

            df = pd.read_csv(regret_file)
            if {"iter", "regret"}.issubset(df.columns):
                tmp = df[["iter", "regret"]].copy()
                tmp["user"] = user
                tmp["method"] = method
                tmp["hyperparams"] = hyperparams
                tmp = tmp.rename(columns={"iter": "queries"})
                all_data.append(tmp[["user", "method", "hyperparams", "queries", "regret"]])

    if not all_data:
        return pd.DataFrame()

    full_df = pd.concat(all_data, ignore_index=True)
    aggregated = (
        full_df.groupby(["method", "hyperparams", "queries"])["regret"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_regret", "std": "std_regret", "count": "n_users"})
    )
    aggregated["std_regret"] = aggregated["std_regret"].fillna(0.0)
    aggregated["regret"] = aggregated["avg_regret"]
    return aggregated


def analyze_best_df(aggregated_df, target_queries=None):
    if aggregated_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    target_queries = target_queries or TARGET_QUERIES
    df = aggregated_df.copy()

    for prefix in HP_PREFIXES:
        df[prefix] = df["hyperparams"].apply(lambda x: parse_hp(str(x), prefix))

    active_hps = [hp for hp in HP_PREFIXES if df[hp].notna().any()]
    max_queries = df["queries"].max()

    dev_rows = []
    summary_rows = []

    for method in df["method"].unique():
        method_df = df[df["method"] == method]
        final_step_df = method_df[method_df["queries"] == max_queries]
        if final_step_df.empty:
            continue

        best_row = final_step_df.loc[final_step_df["avg_regret"].idxmin()]
        best_hp_values = {hp: best_row[hp] for hp in active_hps}

        mask = method_df["method"] == method
        for hp, val in best_hp_values.items():
            if pd.isna(val):
                mask &= method_df[hp].isna()
            else:
                mask &= method_df[hp] == val

        dev_summary = (
            method_df[mask][["queries", "avg_regret", "std_regret"]]
            .drop_duplicates(subset=["queries"])
            .sort_values("queries")
            .reset_index(drop=True)
        )

        hp_label = ", ".join([f"{k}={v}" for k, v in best_hp_values.items() if v is not None])
        config_label = f"{method} ({hp_label})"

        for _, row in dev_summary.iterrows():
            dev_rows.append(
                {
                    "Method": method,
                    "Config": config_label,
                    "Queries": row["queries"],
                    "AvgRegret": row["avg_regret"],
                    "StdRegret": row["std_regret"],
                }
            )

        for q in target_queries:
            row = dev_summary[dev_summary["queries"] == q]
            if not row.empty:
                summary_rows.append(
                    {
                        "Method": method,
                        "Queries": q,
                        "AvgRegret": row.iloc[0]["avg_regret"],
                        "StdRegret": row.iloc[0]["std_regret"],
                    }
                )

    dev_df = pd.DataFrame(dev_rows)
    summary_df = pd.DataFrame(summary_rows)
    return dev_df, summary_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate regret across users and produce dataframes.")
    parser.add_argument("-d", "--directories", type=str, nargs="+", required=True, help="Directories to process")
    args = parser.parse_args()

    aggregated_df = aggregate_regret(args.directories)
    if aggregated_df.empty:
        print("No data found.")
        raise SystemExit(0)

    dev_df, _ = analyze_best_df(aggregated_df, target_queries=TARGET_QUERIES)
    if not dev_df.empty:
        final_df = (
            dev_df[["Method", "Queries", "AvgRegret", "StdRegret"]]
            .drop_duplicates()
            .sort_values(["Method", "Queries"])
            .reset_index(drop=True)
        )
    else:
        final_df = pd.DataFrame(columns=["Method", "Queries", "AvgRegret", "StdRegret"])

    os.makedirs("results", exist_ok=True)
    output_path = os.path.join("results", "results.csv")
    final_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")
