# Milestone 5 local retrieval review

The three requested queries were run against the existing 3 indexed documents
and 206 chunks using real `all-MiniLM-L6-v2` embeddings, pgvector cosine distance,
`top_k=5`, and similarity cutoff 0.2. No source records or titles were changed.

All 15 returned chunk texts were checked against text extracted from their cited
PDF page. Citations use physical PDF page positions, not printed page labels.
Stored document titles are null; labels therefore use exact source filenames.
The observations below are a small manual review, not a retrieval benchmark.

## Pakistan policy and critical infrastructure

Query: `What does Pakistan's cyber security policy say about critical infrastructure?`

All five results are from `2021-National-Cyber-Security-Policy-Final.pdf`.

| Rank | PDF page | Chunk index | Similarity | Passage assessment |
|---|---:|---:|---:|---|
| 1 | 9 | 20 | 0.6988 | Broad vision/scope/objectives, including protecting national information systems and infrastructure |
| 2 | 8 | 19 | 0.6984 | Policy and governance context; does not directly explain critical infrastructure protection |
| 3 | 1 | 0 | 0.6934 | Cover page; identifies the source but supplies no substantive answer |
| 4 | 11 | 24 | 0.6899 | Direct CI/CII passage: attacks are treated as aggression against sovereignty and met with response measures |
| 5 | 8 | 18 | 0.6803 | Broad security capabilities, standards, regulation, and industry context |

Useful direct citation: `[2021-National-Cyber-Security-Policy-Final.pdf, p. 11]`.
Its printed page label is 8; the stored/reference PDF page is 11. Top-1 is related
but broad; more directly relevant evidence ranked fourth.

## NIST CSF 2.0 and incident response

Query: `How does NIST CSF 2.0 address incident response?`

All five results are from `NIST.CSWP.29.pdf`.

| Rank | PDF page | Chunk index | Similarity | Passage assessment |
|---|---:|---:|---:|---|
| 1 | 27 | 76 | 0.6355 | Direct RESPOND guidance: execute the response plan, triage/validate, categorize/prioritize, escalate, and investigate |
| 2 | 2 | 3 | 0.6043 | Reader/resource notes, not substantive response guidance |
| 3 | 3 | 4 | 0.5992 | Acknowledgments, not substantive response guidance |
| 4 | 1 | 0 | 0.5599 | Cover/identification material |
| 5 | 28 | 79 | 0.5583 | Related recovery actions, restoration verification, and recovery communication |

Direct citation: `[NIST.CSWP.29.pdf, p. 27]`. This corresponds to printed page 22.
The top result is directly relevant; lower ranks demonstrate that a moderately
high similarity does not guarantee useful answer evidence.

## CyberSage casebook ransomware incidents

Query: `What happened in the ransomware incidents described in the CyberSage casebook?`

All five results are from `CyberSage_Security_Incident_Casebook_RAG_v2.pdf`.

| Rank | PDF page | Chunk index | Similarity | Passage assessment |
|---|---:|---:|---:|---|
| 1 | 3 | 4 | 0.6560 | Direct ransomware case CS-INC-002: rapid file renaming and an unsigned encryption process on a shared drive |
| 2 | 18 | 49 | 0.5242 | Backup deletion attempt involving five recovery points; related topic, not proof of a ransomware incident |
| 3 | 12 | 31 | 0.5138 | Removable-media malware, not specifically ransomware |
| 4 | 15 | 40 | 0.4995 | Insider bulk downloads, not ransomware |
| 5 | 4 | 7 | 0.4973 | Public cloud storage exposure, not ransomware |

Direct citation: `[CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 3]`.
The casebook explicitly describes synthetic incident records. Top-1 supports the
detection portion of the ransomware case; this retrieved chunk alone does not
establish a complete timeline, containment outcome, or all ransomware incidents.

## Validation and limitations

- Full automated suite: **100 passed**, including 10 real PostgreSQL tests (five
  ingestion tests and five retrieval tests). Offline suite: **90 passed,
  10 PostgreSQL tests intentionally skipped**. No dependencies were added.
- A running Uvicorn server on localhost:8001 returned HTTP 200 for the health
  endpoint and all three searches. All 15 result chunk IDs matched the in-process
  real-model API checks. Invalid query/top-k requests returned HTTP 422. Automated
  tests also verified safe HTTP 503 responses for database/model setup failures.
- Real-model API smoke checks returned five results per requested query, with all
  15 passages matching the cited local PDF page text and consistent cosine scores.
- A similarity cutoff of 1.0 returned no evidence for the first sample query.
- Whitespace queries and top-k values above 20 returned HTTP 422.
- Ingestion rerun skipped all 3 documents, inserted 0 chunks, and had 0 failures.
  Verification retained 3 indexed documents / 206 chunks and zero invalid page
  references, dimensions, norms, orphan chunks, or duplicate indices.
- The cutoff remains permissive and unevaluated. No reranker, lexical/hybrid
  search, header filtering, source diversity policy, or answer generation was added.
- Exact scoring favors reproducible ranking for this small corpus; scaling needs
  separate performance evaluation. The existing HNSW index is untouched.
- A citation identifies where a passage came from; it does not establish truth,
  completeness, or correctness of an answer inferred from that passage.
