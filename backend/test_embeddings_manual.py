"""Run from backend: python test_embeddings_manual.py (downloads on first use)."""

from math import isclose, sqrt

from app.embeddings import embed_text


def main() -> None:
    embedding = embed_text(
        "Multi-factor authentication helps prevent unauthorized account access."
    )
    print(f"Embedding dimensions: {len(embedding)}")
    print(f"First five values: {embedding[:5]}")
    norm = sqrt(sum(value * value for value in embedding))
    assert len(embedding) == 384
    assert isclose(norm, 1.0, abs_tol=1e-5), f"Unexpected L2 norm: {norm}"
    print(f"L2 norm: {norm:.6f}")


if __name__ == "__main__":
    main()
