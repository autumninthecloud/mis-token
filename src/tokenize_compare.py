"""
Compare token counts between clean and typo'd prompts across tokenizers.

Requires: tiktoken, transformers (for non-OpenAI tokenizers), pandas.
Install locally with:
    pip install tiktoken transformers pandas --break-system-packages

Run:
    python tokenize_compare.py --input data/prompts.txt --out results/token_counts.csv
"""

import argparse
import csv
from pathlib import Path

from typo_injector import batch_inject

SEVERITIES = [0.0, 0.05, 0.15, 0.30]
SEED = 42


def load_tokenizers(names: list[str]):
    """Lazily load only the tokenizers the user asked for, so the script
    still runs if e.g. transformers isn't installed and you only want
    tiktoken results."""
    tokenizers = {}

    if any(n in ("cl100k_base", "o200k_base") for n in names):
        import tiktoken
        for n in names:
            if n in ("cl100k_base", "o200k_base"):
                enc = tiktoken.get_encoding(n)
                tokenizers[n] = lambda text, enc=enc: enc.encode(text)

    hf_names = [n for n in names if n not in ("cl100k_base", "o200k_base")]
    if hf_names:
        from transformers import AutoTokenizer
        for n in hf_names:
            tok = AutoTokenizer.from_pretrained(n)
            tokenizers[n] = lambda text, tok=tok: tok.encode(text, add_special_tokens=False)

    return tokenizers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/prompts.txt",
                         help="One prompt per line.")
    parser.add_argument("--out", default="results/token_counts.csv")
    parser.add_argument(
        "--tokenizers", nargs="+",
        default=["cl100k_base", "o200k_base"],
        help="tiktoken encoding names (cl100k_base, o200k_base) and/or "
             "HF model ids (e.g. meta-llama/Llama-3.1-8B, mistralai/Mistral-7B-v0.1). "
             "HF gated models need `huggingface-cli login` first."
    )
    args = parser.parse_args()

    prompts = [
        line.strip() for line in Path(args.input).read_text().splitlines()
        if line.strip()
    ]
    print(f"Loaded {len(prompts)} prompts.")

    tokenizers = load_tokenizers(args.tokenizers)
    print(f"Using tokenizers: {list(tokenizers.keys())}")

    rows = []
    for severity in SEVERITIES:
        noisy_prompts = batch_inject(prompts, severity, seed=SEED)
        for prompt_id, (clean, noisy) in enumerate(zip(prompts, noisy_prompts)):
            for tok_name, encode in tokenizers.items():
                n_tokens = len(encode(noisy))
                rows.append({
                    "prompt_id": prompt_id,
                    "severity": severity,
                    "tokenizer": tok_name,
                    "n_tokens": n_tokens,
                    "n_chars": len(noisy),
                    "n_words": len(noisy.split()),
                    "text": noisy,
                })

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
