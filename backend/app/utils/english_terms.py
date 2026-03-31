"""
Laris - English Terms for SSML <lang> tagging.
Used to wrap English words/phrases in PT-BR text with <lang xml:lang="en-US">
so edge-tts pronounces them correctly.

Add terms and acronyms here to expand coverage.
"""

import re

# ── Multi-word phrases (longest first so alternation matches greedily) ──────
ENGLISH_PHRASES = [
    # Methodology
    "randomized controlled trial",
    "controlled trial",
    "cognitive-behavioral therapy",
    "cognitive behavioral therapy",
    "mindfulness-based intervention",
    "mindfulness-based",
    "self-reported",
    "self-report",
    "follow-up",
    "follow up",
    "drop-out",
    "drop out",
    "dropout rate",
    "sample size",
    "confidence interval",
    "odds ratio",
    "hazard ratio",
    "effect size",
    "p-value",
    "well-being",
    "wellbeing",
    # Academic structure
    "abstract",
    "background",
    "keywords",
    "key words",
    "conclusion",
    "limitations",
    "checklist",
    "benchmark",
    "feedback",
    "outcome",
    "outcomes",
    "endpoint",
    "endpoints",
    "baseline",
    "burnout",
    "mindfulness",
    "dropout",
    # English connectors used in academic PT text
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "nevertheless",
    "nonetheless",
    "whereas",
    "although",
    "thus",
    "hence",
    "indeed",
]

# ── Standalone acronyms (case-sensitive, all-caps) ────────────────────────
ENGLISH_ACRONYMS = [
    # Psychiatry / psychology
    "PTSD", "ADHD", "GAD", "OCD", "DSM", "ICD",
    "CBT", "DBT", "ACT", "EMDR",
    # Methodology
    "RCT", "RCTs",
    # Medicine / biology
    "MRI", "fMRI", "EEG", "ECG", "EKG", "BMI",
    "HIV", "AIDS", "COVID",
    "PCR", "ICU", "ER", "OR",
    # Stats
    "CI", "SD", "SE", "OR",
]

# ── Build compiled regexes ────────────────────────────────────────────────

# Phrases: sort longest-first to prevent partial matches
_phrases_sorted = sorted(ENGLISH_PHRASES, key=len, reverse=True)
_phrases_pattern = r'\b(?:' + '|'.join(re.escape(p) for p in _phrases_sorted) + r')\b'
ENGLISH_TERMS_RE = re.compile(_phrases_pattern, re.IGNORECASE)

# Acronyms: word-boundary, case-sensitive
_acronyms_pattern = r'\b(?:' + '|'.join(re.escape(a) for a in ENGLISH_ACRONYMS) + r')\b'
ENGLISH_ACRONYMS_RE = re.compile(_acronyms_pattern)
