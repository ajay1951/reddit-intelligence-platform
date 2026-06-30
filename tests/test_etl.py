from backend.etl.cleaning import clean_text, normalize_author, normalize_url
from backend.etl.pipeline import _make_comment_id


def test_clean_text_strips_html_and_normalizes_whitespace():
    raw = "<p>Hello <strong>world</strong>\n\nThis is a test.</p>"
    cleaned = clean_text(raw)

    assert cleaned == "Hello world This is a test."


def test_normalize_url_returns_canonical_form():
    url = "HTTPS://old.reddit.com/r/Python/"
    normalized = normalize_url(url)

    assert normalized == "https://old.reddit.com/r/Python"


def test_normalize_author_handles_deleted_names():
    assert normalize_author("[deleted]") is None
    assert normalize_author(" u/test ") == "u/test"


def test_make_comment_id_is_within_bigint_range():
    large_id = "2234250032686288943938"
    comment_id = _make_comment_id(large_id, "u/test", "Example content")

    assert isinstance(comment_id, int)
    assert 0 < comment_id < 2**63
