# CyberSage: recorded 10-question evaluation

Run status: **complete**. Dataset: **8 answerable / 2 unanswerable**.

These are recorded responses, not model examples. Manual grades are separate from lexical signals.

| ID | Expected | Observed status | Capability | Seconds | Manual grade |
|---|---|---|---|---:|---|
| P01 | answerable | answered | knowledge | 3.9961 | pass |
| P02 | answerable | answered | knowledge | 2.5834 | pass |
| P03 | answerable | answered | knowledge | 3.3845 | partial |
| N01 | answerable | answered | knowledge | 4.885 | pass |
| N02 | answerable | answered | knowledge | 3.2145 | pass |
| N03 | answerable | insufficient_evidence | knowledge | 1.2439 | fail |
| C01 | answerable | insufficient_evidence | knowledge | 1.4718 | fail |
| C02 | answerable | answered | knowledge | 3.1964 | pass |
| U01 | unanswerable | insufficient_evidence | knowledge | 1.2567 | pass |
| U02 | unanswerable | insufficient_evidence | knowledge | 1.0734 | pass |

## Metrics

```json
{
  "dataset_questions": 10,
  "executed_count": 10,
  "answered_count": 6,
  "correct_abstention_count": 2,
  "incorrect_abstention_count": 2,
  "unsupported_answer_count": 0,
  "unsupported_count_scope": "unanswerable answers + manually unsupported answers",
  "citations_checked": 12,
  "citation_metadata_valid_count": 12,
  "citation_metadata_valid_rate": 1.0,
  "citation_provenance_valid_count": 12,
  "citation_provenance_valid_rate": 1.0,
  "citation_source_relevant_count": 12,
  "citation_source_relevant_rate": 1.0,
  "lexical_criteria_met": 15,
  "criteria_total": 21,
  "lexical_coverage_rate": 0.7142857142857143,
  "manually_reviewed_answerable_questions": 8,
  "manual_criteria_met": 15,
  "manual_criteria_total": 21,
  "manual_coverage_rate": 0.7142857142857143,
  "average_response_latency_seconds": 2.63057,
  "failure_counts": {
    "incomplete_answer": 1,
    "incorrect_abstention": 2
  }
}
```

Metadata validity and source-filename matches do not prove factual support or completeness.

## Question-by-question observations

### P01: How does Pakistan's National Cyber Security Policy 2021 treat cyber-attacks on critical infrastructure and respond to them?

Expected source/pages: `2021-National-Cyber-Security-Policy-Final.pdf` / [11]. Tests a specific national-policy statement, not an invented list of defensive actions.

Expected criteria:
- sovereignty: Treats CI/CII cyber-attacks as aggression against national sovereignty (PDF p. 11)
- response: Defends itself with appropriate response measures (PDF p. 11)

Actual answer:

> Policy source: "Will regard a cyber-attack on Pakistan CI/ CII as an act of aggression against national sovereignty and will defend itself with appropriate response measures." [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] (E_25a5728633a04d78928c5daeaaf524c9)
>
> Policy source: "Will act per national and international Cyber Security frameworks, standards and best practices and expect reciprocal respect of our national digital sovereignty." [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] (E_25a5728633a04d78928c5daeaaf524c9)

Observed failure signal: `None`; error: `None`.

Citations:
- [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] — `E_25a5728633a04d78928c5daeaaf524c9`, chunk index 24
- [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] — `E_25a5728633a04d78928c5daeaaf524c9`, chunk index 24

Manual review: Pass. The quoted policy p. 11 explicitly treats CI/CII attacks as aggression against national sovereignty and promises appropriate response measures. The additional reciprocal-sovereignty passage is supported but not required.

### P02: What is the vision of Pakistan's National Cyber Security Policy 2021?

Expected source/pages: `2021-National-Cyber-Security-Policy-Final.pdf` / [9]. Tests vision coverage rather than treating a related governance passage as a complete answer.

Expected criteria:
- ecosystem: Secure, robust, continually improving nationwide digital ecosystem (PDF p. 9)
- cia: Confidentiality, integrity, and availability of digital assets (PDF p. 9)
- development: Socio-economic development and national security (PDF p. 9)

Actual answer:

> Policy source: "The vision is for Pakistan to have a secure, robust, and continually improving nationwide digital ecosystem ensuring accountable confidentiality, integrity, and availability of digital assets leading to socio-economic development and national security." [2021-National-Cyber-Security-Policy-Final.pdf, p. 9] (E_89ae0d155c7542ffbe2152fa620b6fa6)

Observed failure signal: `None`; error: `None`.

Citations:
- [2021-National-Cyber-Security-Policy-Final.pdf, p. 9] — `E_89ae0d155c7542ffbe2152fa620b6fa6`, chunk index 20

Manual review: Pass. The p. 9 vision quote covers secure, robust and continually improving nationwide digital infrastructure; accountable confidentiality, integrity and availability; socioeconomic development and national security.

### P03: What oversight and policy-formulation functions does Pakistan's Cyber Governance Policy Committee (CGPC) have?

Expected source/pages: `2021-National-Cyber-Security-Policy-Final.pdf` / [11]. Tests coverage of separate governance functions in a single verified source page.

Expected criteria:
- oversight: Strategic oversight over national cybersecurity issues (PDF p. 11)
- formulation: Formulate, guide, and recommend approval of policy and Act (PDF p. 11)
- reviews: Guide updates and periodic reviews for emerging cyberspace requirements (PDF p. 11)

Actual answer:

> Policy source: "Cyber Governance Policy Committee is responsible for strategic oversight over national Cyber Security issues." [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] (E_25a5728633a04d78928c5daeaaf524c9)
>
> Policy source: "Formulate, guide, and recommend for the approval of the National Cyber Security Policy and Cyber Security Act." [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] (E_25a5728633a04d78928c5daeaaf524c9)

Observed failure signal: `incomplete_answer`; error: `None`.

Citations:
- [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] — `E_25a5728633a04d78928c5daeaaf524c9`, chunk index 24
- [2021-National-Cyber-Security-Policy-Final.pdf, p. 11] — `E_25a5728633a04d78928c5daeaaf524c9`, chunk index 24

Manual review: Partial. The p. 11 quotes support strategic oversight and formulation/recommendation of policy and legislation. They omit the requested updates/periodic-review responsibility, verified in the next database chunk (index 25), which is absent from the diagnostic top five.

### N01: How does NIST CSF 2.0 address incident response plan execution, incident triage, and prioritization?

Expected source/pages: `NIST.CSWP.29.pdf` / [27]. Tests three explicit RS.MA outcomes; matching the RESPOND heading alone is incomplete.

Expected criteria:
- plan: Execute the plan with relevant third parties after declaration (PDF p. 27)
- triage: Triage and validate reports (PDF p. 27)
- priority: Categorize and prioritize incidents (PDF p. 27)

Actual answer:

> Framework guidance: "RS.MA-01: The incident response plan is executed in coordination with relevant third parties once an incident is declared" [NIST.CSWP.29.pdf, p. 27] (E_45eebff5cd2b40b6879df1161f0d7452)
>
> Framework guidance: "RS.MA-02: Incident reports are triaged and validated" [NIST.CSWP.29.pdf, p. 27] (E_45eebff5cd2b40b6879df1161f0d7452)
>
> Framework guidance: "RS.MA-03: Incidents are categorized and prioritized" [NIST.CSWP.29.pdf, p. 27] (E_45eebff5cd2b40b6879df1161f0d7452)

Observed failure signal: `None`; error: `None`.

Citations:
- [NIST.CSWP.29.pdf, p. 27] — `E_45eebff5cd2b40b6879df1161f0d7452`, chunk index 76
- [NIST.CSWP.29.pdf, p. 27] — `E_45eebff5cd2b40b6879df1161f0d7452`, chunk index 76
- [NIST.CSWP.29.pdf, p. 27] — `E_45eebff5cd2b40b6879df1161f0d7452`, chunk index 76

Manual review: Pass. The p. 27 RS.MA-01, RS.MA-02 and RS.MA-03 quotes cover coordinated plan execution, triage/validation, and categorization/prioritization. Physical PDF p. 27 is the printed body page 22.

### N02: What does NIST CSF 2.0 say about verifying backup and restored-system integrity during recovery?

Expected source/pages: `NIST.CSWP.29.pdf` / [28]. Tests recovery controls, including the distinction between checking backups and restored systems.

Expected criteria:
- backups: Verify backups/restoration assets before use (PDF p. 28)
- restored: Verify restored assets and confirm normal operations (PDF p. 28)

Actual answer:

> Framework guidance: "RC.RP-03: The integrity of backups and other restoration assets is verified before using them for restoration" [NIST.CSWP.29.pdf, p. 28] (E_b4fe26f3294d4a62abaccaa24ef67707)
>
> Framework guidance: "RC.RP-05: The integrity of restored assets is verified, systems and services are restored, and normal operating status is confirmed" [NIST.CSWP.29.pdf, p. 28] (E_b4fe26f3294d4a62abaccaa24ef67707)

Observed failure signal: `None`; error: `None`.

Citations:
- [NIST.CSWP.29.pdf, p. 28] — `E_b4fe26f3294d4a62abaccaa24ef67707`, chunk index 79
- [NIST.CSWP.29.pdf, p. 28] — `E_b4fe26f3294d4a62abaccaa24ef67707`, chunk index 79

Manual review: Pass. The p. 28 RC.RP-03 and RC.RP-05 excerpts distinguish checking restoration assets before use from checking restored assets, restoring services, and confirming normal operation.

### N03: Under NIST CSF 2.0 DE.AE-08, when are incidents declared?

Expected source/pages: `NIST.CSWP.29.pdf` / [26]. Tests a precise DETECT outcome; no real incident or numerical score should be invented.

Expected criteria:
- criteria: Declare incidents when adverse events meet defined incident criteria (PDF p. 26)

Actual answer:

> The available source evidence is insufficient to answer this question reliably.

Observed failure signal: `incorrect_abstention`; error: `None`.

Citations:

Manual review: Fail: incorrect abstention. DE.AE-08 is explicit on PDF p. 26, database chunk 75. The diagnostic retrieval returned NIST chunks 76, 57, 77, 79 and 26, omitting chunk 75. Production reported model_abstained; do not call this a citation validation failure.

### C01: In the CyberSage synthetic casebook CS-INC-002, how was ransomware detected, contained, and recovered from, and was a ransom paid?

Expected source/pages: `CyberSage_Security_Incident_Casebook_RAG_v2.pdf` / [3]. Tests multi-chunk incident coverage and explicit synthetic/fictional labeling; triage labels are not evidence of outcome.

Expected criteria:
- detect: Rapid renaming and unsigned encryption process (PDF p. 3)
- contain: Workstation isolated and compromised credentials disabled (PDF p. 3)
- restore: Restore affected files from verified offline backup (PDF p. 3)
- ransom: Recovery completed without ransom payment (PDF p. 3)

Actual answer:

> The available source evidence is insufficient to answer this question reliably.

Observed failure signal: `incorrect_abstention`; error: `None`.

Citations:

Manual review: Fail: incorrect abstention. PDF p. 3 contains all four criteria. Diagnostic rank one (chunk 4) contains the incident header/detection only; chunk 5 containing containment, backup recovery and no-ransom outcome is missing. Production reported model_abstained. No synthetic narrative was falsely presented as real.

### C02: In the CyberSage synthetic casebook CS-INC-017, what happened to the five backup deletion requests and what containment controls were applied?

Expected source/pages: `CyberSage_Security_Incident_Casebook_RAG_v2.pdf` / [18]. Tests confirmed outcome versus a mere attempted deletion, with synthetic incident labeling.

Expected criteria:
- outcome: All five requests failed and restore points remained available (PDF p. 18)
- token: Disable service token (PDF p. 18)
- controls: Immutable backups and restricted break-glass deletion permissions (PDF p. 18)

Actual answer:

> Synthetic incident example (not a real event): "All five deletion requests failed; restore points remained available." [CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 18] (E_d733973e7284436dbb7e91bdf7e313a9)
>
> Synthetic incident example (not a real event): "Containment and recovery Disabled the service token, enforced immutable backups, and restricted delete permissions to a break-glass role." [CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 18] (E_d733973e7284436dbb7e91bdf7e313a9)

Observed failure signal: `None`; error: `None`.

Citations:
- [CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 18] — `E_d733973e7284436dbb7e91bdf7e313a9`, chunk index 50
- [CyberSage_Security_Incident_Casebook_RAG_v2.pdf, p. 18] — `E_d733973e7284436dbb7e91bdf7e313a9`, chunk index 50

Manual review: Pass. Both p. 18 quotes are supported: all five deletion attempts failed, restore points remained, and the service token was disabled with immutable backups and break-glass deletion controls. Both excerpts explicitly say synthetic incident example (not a real event).

### U01: What is the cybersecurity policy of Mars in 2050?

Expected source/pages: `None` / none. No indexed PDF documents a Martian cybersecurity policy. Require explicit insufficient evidence with no citations.

Expected criteria:

Actual answer:

> The available source evidence is insufficient to answer this question reliably.

Observed failure signal: `None`; error: `None`.

Citations:

Manual review: Pass: correct abstention, fixed insufficient-evidence answer and zero citations. None of these PDFs documents a Mars policy in 2050.

### U02: What is the exact SHA-256 hash of the malware used in CyberSage casebook incident CS-INC-002?

Expected source/pages: `None` / none. The case record describes ransomware but supplies no malware SHA-256. Require abstention rather than an invented hash.

Expected criteria:

Actual answer:

> The available source evidence is insufficient to answer this question reliably.

Observed failure signal: `None`; error: `None`.

Citations:

Manual review: Pass: correct abstention with zero citations. The casebook supplies no malware SHA-256; the source excerpt check confirms no 64-character hash on the relevant page.
