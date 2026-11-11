from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []

    for page in pages:
        text_chunks = splitter.split_text(page["content"])

        for text in text_chunks:
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "page_number": page["page_number"],
                    "content": text,
                }
            )

    return chunks
