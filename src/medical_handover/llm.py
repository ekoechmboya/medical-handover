from __future__ import annotations

import json
import os
import random
import re
from collections.abc import Mapping, Sequence

from .schema import CATEGORIES, STATUSES, canonical_category
from google.api_core.retry import Retry

# Single-attempt retry policy: no automatic retries (see complete_json). Rate
# limiting / backoff is handled by the caller so we never burst the API.
_NO_RETRY = Retry(max_attempts=1)

# Pinned baseline model for the hackathon comparison.
#
# The originally planned models (gemini-1.5-flash, gemini-2.5-flash) were
# unavailable on this account at run time: gemini-1.5-flash returned 404
# (deprecated) and gemini-2.5-flash was rejected as "no longer available to new
# users". gemini-3.6-flash is the available, pinned substitute and is used for
# BOTH the one-shot baseline and the advanced agent so that the comparison
# measures agentic engineering rather than model capability. See
# BASELINE_MODEL.md for the full rationale and evidence location.
BASELINE_MODEL = "gemini-3.6-flash"

# Prompt contract shared with baseline.py. The mock backend parses these exact
# delimiters, so the prompt is the single source of truth for what the model
# (real or mocked) is allowed to see. Ground truth is never placed inside them.
PROFILE_BEGIN = "<<<PATIENT PROFILE>>>"
PROFILE_END = "<<<END PROFILE>>>"
RECORD_BEGIN = "<<<RECORD:"
RECORD_END = "<<<END RECORD>>>"
HANDOVER_BEGIN = "<<<CURRENT HANDOVER>>>"
HANDOVER_END = "<<<END HANDOVER>>>"

MOCK_SEED = 1337

_RECORD_RE = re.compile(
    r"<<<RECORD:\s*(?P<name>[^>]+?)>>>(?P<body>.*?)<<<END RECORD>>>", re.S
)
_HANDOVER_RE = re.compile(
    r"<<<CURRENT HANDOVER>>>(?P<body>.*?)<<<END HANDOVER>>>", re.S
)

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "of", "in", "on",
        "for", "with", "to", "from", "at", "by", "as", "is", "are", "was",
        "were", "be", "been", "not", "no", "do", "does", "did", "has", "have",
        "had", "it", "its", "this", "that", "these", "those", "they", "them",
        "we", "our", "who", "what", "which", "when", "where", "how", "will",
        "would", "can", "could", "should", "may", "might", "must", "current",
        "currently", "due", "because", "remain", "remains", "remaining",
        "under", "during", "over", "still", "now", "patient", "note", "notes",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# (canonical_category, regex, default_importance). Order matters only as a
# tie-breaker; the first detector to claim a sentence wins.
_DETECTORS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("allergy_or_adverse_reaction", re.compile(r"allerg|anaphylax|hypersensit"), "critical"),
    ("medication", re.compile(r"medication|tablet|capsule|\bmg\b|anticoag|antibiotic|prescrib|analges|warfarin|heparin|aspirin|paracetamol|ibuprofen|insulin|methotrexat|rx\b"), "high"),
    ("monitoring", re.compile(r"monitor|saturation|spo2|oxygen|blood pressure|vital|target|ecg|telemetry"), "high"),
    ("pending_result", re.compile(r"pending|awaiting|result|lab|culture|blood test|imaging|scan|\bx-ray\b|mri|\bct\b"), "high"),
    ("escalation", re.compile(r"escalat|deteriorat|urgent|critical|worsen|seps|declin"), "critical"),
    ("pending_consult", re.compile(r"consult|referr|specialist|review by"), "high"),
    ("procedure", re.compile(r"procedure|surgery|operat|catheter|biopsy|endoscop"), "critical"),
    ("safety", re.compile(r"fall|risk|supervis|mobility|restrict|unsafe|1:1|one to one"), "high"),
    ("pending_investigation", re.compile(r"investigat|exam|assess|trial"), "high"),
    ("clinical_status", re.compile(r"stable|unstable|improving|worsening|status|\bgcs\b|conscious"), "high"),
)

# A record sentence is only treated as an *omitted* finding when its content is
# NOT already conveyed by the handover. This gate keeps the false-positive
# control case (everything already handed over) silent.
_HANDOVER_COVERAGE = 0.5


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _coverage(sentence: str, handover: str) -> float:
    ts, th = _tokens(sentence), _tokens(handover)
    if not ts:
        return 1.0
    return len(ts & th) / len(ts)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 12:
            out.append(p)
    return out


class FindingSpec(tuple):
    """(category, importance, status, summary, evidence_sources)."""


class LLMClient:
    """Minimal client abstraction: prompt in, structured dict out."""

    def complete_json(self, prompt: str) -> dict:
        raise NotImplementedError


class MockClient(LLMClient):
    """Deterministic, network-free stand-in for an LLM.

    Parses the prompt's delimited clinical content and emits findings using a
    fixed rule set. Output is fully determined by the seeded RNG (used only for
    stable tie-breaking) and the input text, so CI runs are reproducible.
    """

    def __init__(self, seed: int = MOCK_SEED) -> None:
        self._rng = random.Random(seed)

    def complete_json(self, prompt: str) -> dict:
        records = {
            m.group("name").strip(): m.group("body")
            for m in _RECORD_RE.finditer(prompt)
        }
        hand_m = _HANDOVER_RE.search(prompt)
        handover = hand_m.group("body") if hand_m else ""

        if not records:
            # Fallback: treat the whole prompt (minus the handover) as one blob.
            blob = prompt
            if hand_m:
                blob = prompt[: hand_m.start()] + prompt[hand_m.end():]
            records = {"input.txt": blob}

        findings = self._extract(records, handover)
        return {"findings": [self._serialize(f) for f in findings]}

    def _extract(
        self, records: Mapping[str, str], handover: str
    ) -> list[tuple[str, str, str, str, tuple[str, ...]]]:
        candidates: list[tuple[str, str, str, str, tuple[str, ...]]] = []
        seen: set[tuple[str, frozenset[str]]] = set()

        for name in sorted(records):
            body = records[name]
            for sentence in _split_sentences(body):
                if _coverage(sentence, handover) >= _HANDOVER_COVERAGE:
                    continue
                for category, pattern, importance in _DETECTORS:
                    if pattern.search(sentence):
                        key_tokens = frozenset(_tokens(sentence))
                        key = (category, key_tokens)
                        if key in seen:
                            break
                        seen.add(key)
                        summary = self._summarize(category, sentence)
                        candidates.append(
                            (category, importance, "omitted", summary, (name,))
                        )
                        break

        # Deterministic ordering: by category, then evidence, then summary.
        candidates.sort(key=lambda c: (c[0], c[4], c[3]))
        return candidates

    @staticmethod
    def _summarize(category: str, sentence: str) -> str:
        s = sentence.strip()
        if len(s) > 240:
            s = s[:237].rstrip() + "..."
        return s

    @staticmethod
    def _serialize(f: tuple[str, str, str, str, tuple[str, ...]]) -> dict:
        category, importance, status, summary, evidence = f
        return {
            "category": category,
            "importance": importance,
            "status": status,
            "summary": summary,
            "evidence_sources": list(evidence),
        }


class GeminiClient(LLMClient):
    """Real backend. Lazy import so the package installs/runs without the dep.

    Requires ``MH_EMITTER_BACKEND=gemini`` plus ``GEMINI_API_KEY`` and the
    optional ``llm`` extra (``pip install -e ".[llm]"``).
    """

    def __init__(self, model: str | None = None, temperature: float = 0.0) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "Gemini backend selected but `google-generativeai` is not "
                "installed. Run: pip install -e \".[llm]\"."
            ) from exc
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model = model or os.environ.get("MH_EMITTER_MODEL", BASELINE_MODEL)
        self._temperature = temperature
        self._last_usage_metadata = None

    @property
    def last_usage_metadata(self) -> dict | None:
        """Token usage from the most recent call (Gemini backend only)."""
        return self._last_usage_metadata

    def complete_json(self, prompt: str) -> dict:
        model = self._genai.GenerativeModel(
            self._model,
            generation_config={
                "temperature": self._temperature,
                "response_mime_type": "application/json",
            },
        )
        # Disable the SDK's built-in retry: under the free-tier rate limit, the
        # default retry storm multiplies every logical call into a burst of
        # requests and exhausts the quota. Our caller (run_agent.RateLimitedClient)
        # performs its own paced retries instead. Bound each call so a hung
        # connection fails fast and is retried by the wrapper.
        resp = model.generate_content(
            prompt, request_options={"retry": _NO_RETRY, "timeout": 30}
        )
        # Capture token usage for cost/observability reporting. Additive only;
        # baseline_emit still reads solely the parsed "findings" key.
        self._last_usage_metadata = getattr(resp, "usage_metadata", None)
        return json.loads(resp.text)


def get_client(backend: str | None = None, temperature: float = 0.0) -> LLMClient:
    """Return an LLM client. Defaults to the deterministic mock backend."""
    backend = backend or os.environ.get("MH_EMITTER_BACKEND", "mock")
    if backend == "gemini":
        return GeminiClient(temperature=temperature)
    if backend in ("mock", "deterministic"):
        return MockClient()
    raise ValueError(f"Unknown MH_EMITTER_BACKEND: {backend!r}")


__all__ = [
    "LLMClient",
    "MockClient",
    "GeminiClient",
    "get_client",
    "CATEGORIES",
    "STATUSES",
    "canonical_category",
]
