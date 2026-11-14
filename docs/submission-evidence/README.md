# Preserved screenshot evidence

These five PNGs are **byte-for-byte copies** of genuine Milestone 11 local
browser captures, copied from `frontend/.cache/milestone11/` for the university
submission. They were visually inspected before copying. No image was regenerated,
cropped, retouched or composited. The [SHA-256 manifest](manifest.json) records
original paths, sizes and dimensions; its timestamp is the copy time, not a
claim about when each screenshot was captured.

| File | What is visible |
|---|---|
| [overview.png](overview.png) | Product overview and explicitly labeled corpus snapshot |
| [assistant-citations.png](assistant-citations.png) | Actual NIST response and source cards for PDF pp. 27 and 20 |
| [risk-confirmed.png](risk-confirmed.png) | Local preview distinguished from actual server-confirmed 20/Critical result |
| [memory.png](memory.png) | Original recovery follow-up, resolved NIST question, real response and citations |
| [memory-mobile.png](memory-mobile.png) | The saved recovery conversation on mobile, including the focused accessibility skip link |

The memory images show the visible scrolled portion of a persisted conversation,
not the entire history at once. The original first answer is in the separate
assistant screenshot; four-message persistence is recorded in the
[sanitized integration JSON](../milestone11-live-results.json). The risk image
was captured following a real server assessment; it is not a mocked preview.

The images contain no visible API keys, passwords, private configuration, or
conversation access IDs. Visible evidence/chunk identifiers belong to source
citations, not conversation-access credentials. Questions are non-sensitive
assignment examples. No private JSON capture, raw PDF or environment file is
included here. Original screenshots remain unchanged in the ignored cache.
