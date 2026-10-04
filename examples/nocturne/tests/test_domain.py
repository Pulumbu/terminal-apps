"""Domain tests: no event loop, no widgets, fast."""

from nocturne.domain import chunked, filter_entries, generate, level_counts


def test_generate_is_deterministic():
    assert generate(10, seed=1) == generate(10, seed=1)
    assert generate(10, seed=1) != generate(10, seed=2)


def test_filter_by_text_is_case_insensitive():
    entries = generate(200, seed=3)
    assert filter_entries(entries, "TIMEOUT") == filter_entries(entries, "timeout")


def test_filter_by_level():
    entries = generate(200, seed=4)
    only_errors = filter_entries(entries, levels={"error"})
    assert only_errors
    assert {entry.level for entry in only_errors} == {"error"}


def test_filter_combines_text_and_level():
    entries = generate(500, seed=5)
    combined = filter_entries(entries, "retry", levels={"error"})
    assert all(entry.level == "error" and "retry" in entry.message for entry in combined)


def test_level_counts_sum_to_total():
    entries = generate(123, seed=6)
    assert sum(level_counts(entries).values()) == 123


def test_chunked_covers_everything():
    entries = generate(250, seed=7)
    chunks = list(chunked(entries, 60))
    assert [len(chunk) for chunk in chunks] == [60, 60, 60, 60, 10]
    assert [entry for chunk in chunks for entry in chunk] == list(entries)
