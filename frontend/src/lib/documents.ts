/** Verified corpus snapshot from ingestion/Milestone 9; no document-list endpoint exists. */
export const documents = [
  {
    id: "policy",
    short: "PK / 2021",
    title: "National Cyber Security Policy",
    subtitle: "Pakistan · 2021",
    kind: "National policy",
    pages: 22,
    chunks: 52,
    filename: "2021-National-Cyber-Security-Policy-Final.pdf",
    color: "sage",
    description:
      "Pakistan’s vision for a secure digital ecosystem, national governance, and the protection of critical information infrastructure.",
    question:
      "What does Pakistan's National Cyber Security Policy say about critical infrastructure?",
  },
  {
    id: "framework",
    short: "NIST / 2.0",
    title: "Cybersecurity Framework 2.0",
    subtitle: "NIST · 2024",
    kind: "Framework guidance",
    pages: 32,
    chunks: 93,
    filename: "NIST.CSWP.29.pdf",
    color: "blue",
    description:
      "A structured framework to govern, identify, protect, detect, respond, and recover. Guidance for managing cybersecurity risk.",
    question: "How does NIST CSF 2.0 address incident response?",
  },
  {
    id: "casebook",
    short: "CS / V2",
    title: "Security Incident Casebook",
    subtitle: "CyberSage · Version 2",
    kind: "Synthetic examples",
    pages: 21,
    chunks: 61,
    filename: "CyberSage_Security_Incident_Casebook_RAG_v2.pdf",
    color: "sand",
    description:
      "Fictional, Pakistan-focused incident records for learning. These synthetic scenarios are not reports of real-world events.",
    question:
      "In the synthetic casebook CS-INC-017, what happened to the backup deletion requests?",
  },
] as const;
