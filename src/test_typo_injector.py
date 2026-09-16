"""
Quick sanity tests. Run with: python -m pytest test_typo_injector.py -v
(or just `python test_typo_injector.py` for a plain assert run, no pytest needed)
"""

from typo_injector import inject_typos, batch_inject


def test_zero_severity_returns_input_unchanged():
    text = "The quick brown fox jumps over the lazy dog"
    assert inject_typos(text, 0.0, seed=1) == text


def test_severity_one_changes_most_words():
    text = "The quick brown fox jumps over the lazy dog"
    noisy = inject_typos(text, 1.0, seed=1)
    original_words = text.split()
    noisy_words = noisy.split()
    assert len(original_words) == len(noisy_words)
    changed = sum(1 for a, b in zip(original_words, noisy_words) if a != b)
    # allow a little slack: 1-letter words are skipped on purpose
    assert changed >= len(original_words) - 2


def test_reproducible_with_same_seed():
    text = "Could you please summarize this report for me"
    a = inject_typos(text, 0.3, seed=99)
    b = inject_typos(text, 0.3, seed=99)
    assert a == b


def test_word_count_preserved():
    text = "Could you please summarize this report for me"
    noisy = inject_typos(text, 0.5, seed=7)
    assert len(noisy.split()) == len(text.split())


def test_batch_inject_matches_length():
    prompts = ["Hello world", "This is a test prompt", "Another one here"]
    out = batch_inject(prompts, 0.2, seed=5)
    assert len(out) == len(prompts)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
