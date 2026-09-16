"""
Programmatic typo injection.

Implements the four canonical edit types (insertion, substitution, deletion,
transposition), weighted to roughly match the empirical distribution reported
in typo-correction literature (substitution ~39%, insertion ~33%, deletion +
transposition splitting the remainder), and using a QWERTY adjacency map so
substitutions land on physically nearby keys rather than uniformly random
letters -- which is closer to how humans actually mistype.

Usage:
    from typo_injector import inject_typos
    noisy = inject_typos("The quick brown fox", severity=0.15, seed=42)
"""

import random
import string

# QWERTY physical neighbors, lowercase only. Used for substitution and
# insertion so injected errors look like real fat-finger mistakes.
QWERTY_NEIGHBORS = {
    "q": "wa", "w": "qeas", "e": "wrsd", "r": "etdf", "t": "ryfg",
    "y": "tugh", "u": "yihj", "i": "uojk", "o": "ipkl", "p": "ol",
    "a": "qwsz", "s": "awedxz", "d": "serfcx", "f": "drtgvc",
    "g": "ftyhbv", "h": "gyujnb", "j": "huikmn", "k": "jiolm",
    "l": "kop",
    "z": "asx", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn",
    "n": "bhjm", "m": "njk",
}

EDIT_WEIGHTS = {
    "substitution": 0.39,
    "insertion": 0.33,
    "deletion": 0.18,
    "transposition": 0.10,
}


def _pick_edit_type(rng: random.Random) -> str:
    types, weights = zip(*EDIT_WEIGHTS.items())
    return rng.choices(types, weights=weights, k=1)[0]


def _mutate_word(word: str, rng: random.Random) -> str:
    """Apply a single edit to a single word. Leaves punctuation-only or
    1-character words untouched (too easy to fully destroy the token)."""
    letters_only = [c for c in word if c.isalpha()]
    if len(letters_only) < 2:
        return word

    edit = _pick_edit_type(rng)
    idx = rng.randrange(len(word))
    ch = word[idx]

    if edit == "substitution" and ch.lower() in QWERTY_NEIGHBORS:
        neighbor_pool = QWERTY_NEIGHBORS[ch.lower()]
        new_ch = rng.choice(neighbor_pool)
        if ch.isupper():
            new_ch = new_ch.upper()
        return word[:idx] + new_ch + word[idx + 1:]

    if edit == "insertion":
        base = ch.lower() if ch.isalpha() else rng.choice(string.ascii_lowercase)
        neighbor_pool = QWERTY_NEIGHBORS.get(base, string.ascii_lowercase)
        new_ch = rng.choice(neighbor_pool)
        insert_at = idx + rng.choice([0, 1])
        return word[:insert_at] + new_ch + word[insert_at:]

    if edit == "deletion":
        return word[:idx] + word[idx + 1:]

    if edit == "transposition" and idx < len(word) - 1:
        chars = list(word)
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        return "".join(chars)

    # Fallback (e.g. transposition picked on last char, or substitution on
    # a non-letter): just delete a character so *something* changes.
    return word[:idx] + word[idx + 1:]


def inject_typos(text: str, severity: float, seed: int | None = None) -> str:
    """
    Return a copy of `text` with typos injected into approximately
    `severity` fraction of its words.

    severity: float in [0, 1]. E.g. 0.15 -> ~15% of words get one edit.
    seed: optional int for reproducibility. Pass the same seed to get the
    same corruption for the same input across runs.
    """
    if not 0 <= severity <= 1:
        raise ValueError("severity must be between 0 and 1")

    rng = random.Random(seed)
    words = text.split(" ")
    n_to_corrupt = round(len(words) * severity)
    if n_to_corrupt == 0:
        return text

    eligible_idx = [i for i, w in enumerate(words) if sum(c.isalpha() for c in w) >= 2]
    n_to_corrupt = min(n_to_corrupt, len(eligible_idx))
    targets = set(rng.sample(eligible_idx, n_to_corrupt))

    for i in targets:
        words[i] = _mutate_word(words[i], rng)

    return " ".join(words)


def batch_inject(prompts: list[str], severity: float, seed: int | None = None):
    """Apply inject_typos to a list of prompts. Uses a distinct sub-seed per
    prompt (derived from seed + index) so runs are reproducible but prompts
    don't all get identical corruption patterns."""
    out = []
    for i, p in enumerate(prompts):
        sub_seed = None if seed is None else seed + i
        out.append(inject_typos(p, severity, seed=sub_seed))
    return out


if __name__ == "__main__":
    sample = "Could you please summarize the quarterly financial report for me?"
    for sev in (0.0, 0.05, 0.15, 0.30):
        print(f"severity={sev:>4}: {inject_typos(sample, sev, seed=42)}")
