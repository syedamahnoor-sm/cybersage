# CyberSage: 5–7 minute demonstration guide

Target duration: **6 minutes 30 seconds**, with services started before the timed
presentation. This is a script to rehearse, not a claim that a human rehearsal
has already occurred. Use the [submission checklist](submission-checklist.md).

## Before the presentation

Use three terminals. Preserve existing environment files; never display them,
print environment variables, or paste credentials into the assistant.

Repository root:

```powershell
docker compose up -d db
docker compose ps
```

Backend terminal:

```powershell
cd backend
# Optional only when the verified model is already in this cache:
$env:HF_HOME = Join-Path (Get-Location) '.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm.cmd ci
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
# .env.local uses FASTAPI_BASE_URL=http://127.0.0.1:8000; no provider secrets.
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Use `npm` on non-Windows systems. Existing dependencies/environment/corpus are
required; do not reapply migrations or reingest the PDFs during the demo. Fresh
setup is documented in [README](../README.md) and the
[integration guide](milestone11-integration.md). If port 3000 is occupied, choose
another local frontend port and open that address. If the API port changes,
update the frontend's non-secret target and restart it.

Open the UI, the [final report](CyberSage_Final_Assignment_Report.md), and the
[original evaluation](milestone9-results.md). Confirm the API is reachable.
Health proves FastAPI reachability only, not provider/database readiness. Cold
embedding initialization may take time: use a preflight retrieval check before
the timed presentation if needed, without changing indexed documents:

```powershell
$query = @{ query = 'How does NIST CSF 2.0 address incident response?'; top_k = 1 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/retrieval/search -ContentType application/json -Body $query | Select-Object result_count
```

Keep at least 65 seconds between successive Groq questions, as in the recorded
validation. This reduces throttling but cannot guarantee provider capacity.

## Timed presentation

| Time | Action and talking point |
|---|---|
| 0:00–0:35 | **Overview.** “CyberSage connects cybersecurity questions to a curated corpus. These 3 sources, 75 pages and 206 chunks are a verified snapshot, not live threat telemetry.” |
| 0:35–1:20 | **Assistant.** Ask: **What does NIST CSF 2.0 say about incident response?** Explain that retrieval supplies evidence to the Groq-backed bounded agent. Wait for the complete response; no token streaming is simulated. |
| 1:20–2:15 | **Citations and sources.** Expand a returned citation. Show its actual filename, physical PDF page, chunk and quote. The recorded run cited NIST pp. 27 and 20; a new run may choose different valid passages. Explain the policy/framework/synthetic-casebook distinction. Let the first provider cooldown finish before the next question. |
| 2:15–3:15 | **Memory.** In the same conversation ask: **What about recovery?** Show the resolved NIST question. In the recorded run, evidence came from pp. 28 and 27. Refresh the browser or reopen its recent shortcut; verify the original messages remain. Do not expose the conversation ID in a public recording. |
| 3:15–4:15 | **Risk Analyzer.** Select likelihood **4**, impact **5**. Identify the local preview, then click **Confirm assessment**. Show the real server result **20 / Critical**. Explain the illustrative matrix and that no LLM performs the arithmetic. This interval also provides the next Groq cooldown. |
| 4:15–5:00 | **Abstention.** Start a new conversation and ask: **What is the cybersecurity policy of Mars in 2050?** The recorded result was `insufficient_evidence`, with no citations. If the current result differs, report it honestly. |
| 5:00–6:00 | **Evaluation.** Show the original 10-question table: 8 answerable/2 unanswerable; 5 full answer passes, 1 partial, 2 incorrect abstentions, 2 correct abstentions; 15/21 criteria; 12/12 citation records verified. Explain that later successful demos did not replace failures. |
| 6:00–6:30 | **Limits and close.** Show P03's missing neighboring chunk, or N03's missed exact subcategory. Mention no authentication, UUID-based history access, small corpus and incomplete answers. Point to the repository and future evaluation-led retrieval improvements. |

## Handling a genuine failure

- If a request times out or fails, show the error and retry the original request
  using the UI; it preserves the request ID. Do not repeatedly submit new copies.
- If Groq is unavailable or rate limited, stop making generation requests. Use
  the [preserved screenshot evidence](submission-evidence/README.md) and
  [recorded live results](milestone11-live-results.json), clearly saying they are
  prior captured evidence, not a currently successful live response.
- If an answerable question abstains, explain the conservative grounding path
  and the original evaluation failures. Never manufacture an answer/citation.
- If a source page differs from the example, inspect what actually returned.
  PDF page numbers are not necessarily the printed body-page numbers.

Do not edit the original evaluation or regenerate submission evidence during the
presentation. Rehearse the timing, transitions and fallback before November 19.
