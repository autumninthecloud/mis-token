"""
Summarize results/token_counts.csv into the headline fertility-vs-severity
numbers, and (if matplotlib is available) save a chart to results/.

Run after tokenize_compare.py:
    python analyze.py --input results/token_counts.csv
"""

import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/token_counts.csv")
    parser.add_argument("--chart_out", default=None,
                         help="Defaults to fertility_vs_severity.png next to --input.")
    parser.add_argument("--summary_out", default=None,
                         help="Defaults to summary.csv next to --input.")
    args = parser.parse_args()

    input_path = Path(args.input)
    results_dir = input_path.parent
    results_dir.mkdir(parents=True, exist_ok=True)

    chart_out = Path(args.chart_out) if args.chart_out else results_dir / "fertility_vs_severity.png"
    summary_out = Path(args.summary_out) if args.summary_out else results_dir / "summary.csv"

    df = pd.read_csv(input_path)

    # Fertility = tokens per word. Compare each severity level back to the
    # severity=0.0 baseline, per tokenizer, per prompt, then average.
    baseline = (
        df[df.severity == 0.0]
        .set_index(["prompt_id", "tokenizer"])["n_tokens"]
        .rename("baseline_tokens")
    )
    merged = df.join(baseline, on=["prompt_id", "tokenizer"])
    merged["pct_increase"] = (
        (merged["n_tokens"] - merged["baseline_tokens"]) / merged["baseline_tokens"] * 100
    )
    merged["fertility"] = merged["n_tokens"] / merged["n_words"]

    summary = (
        merged.groupby(["tokenizer", "severity"])
        .agg(
            mean_tokens=("n_tokens", "mean"),
            mean_fertility=("fertility", "mean"),
            mean_pct_increase_vs_clean=("pct_increase", "mean"),
        )
        .round(3)
    )
    print(summary)
    summary.to_csv(summary_out)

    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 5))
        for tok_name, group in merged.groupby("tokenizer"):
            grouped = group.groupby("severity")["fertility"].mean()
            ax.plot(grouped.index, grouped.values, marker="o", label=tok_name)
        ax.set_xlabel("Typo severity (fraction of words corrupted)")
        ax.set_ylabel("Mean fertility (tokens / word)")
        ax.set_title("Tokenizer fertility vs. typo severity")
        ax.legend()
        fig.tight_layout()
        fig.savefig(chart_out, dpi=150)
        print(f"Saved chart to {chart_out}")
    except ImportError:
        print("matplotlib not installed; skipping chart. `pip install matplotlib` to enable.")


if __name__ == "__main__":
    main()
