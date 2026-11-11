from app.ingestion.chunker import chunk_pages

def test_chunk_size_limit():
    pages = [{
        "page_number": 1,
        "content": "Cybersecurity incident response. " * 100
    }]

    chunks = chunk_pages(pages)

    assert len(chunks) > 1
    assert all(len(chunk["content"]) <= 1000 for chunk in chunks)


def test_page_numbers_preserved():
    pages = [
        {"page_number": 3, "content": "Security controls."},
        {"page_number": 7, "content": "Incident response."},
    ]

    chunks = chunk_pages(pages)

    assert [chunk["page_number"] for chunk in chunks] == [3, 7]


def test_chunk_indices_sequential():
    pages = [
        {"page_number": 1, "content": "Network security. " * 100},
        {"page_number": 2, "content": "Risk management. " * 100},
    ]

    chunks = chunk_pages(pages)

    assert [chunk["chunk_index"] for chunk in chunks] == list(
        range(len(chunks))
    )


def test_empty_pages():
    pages = [{"page_number": 1, "content": ""}]

    assert chunk_pages(pages) == []
