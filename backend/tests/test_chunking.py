from seed import chunk_text


def test_chunk_text_keeps_content():
    text = "First section.\n\nSecond section.\n\nThird section."
    chunks = chunk_text(text, max_chars=25)
    assert len(chunks) >= 2
    assert "First section." in " ".join(chunks)
    assert "Third section." in " ".join(chunks)
