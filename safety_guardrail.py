"""
Safety & Guardrail Layer
========================
Member 3's deliverable: a pipeline that sits in front of / around a
medicine-information assistant and enforces three checks before any
answer is allowed to reach the user.

    1. Red-flag detection   -> emergency short-circuit
    2. Confidence scoring   -> retrieval + completeness + safety critic
    3. Risk classification  -> LOW / MEDIUM / HIGH -> action

Drop this module next to the rest of the pipeline. The only thing you
need to wire up for real use is:
  - `retrieval_relevance`, `completeness`, `safety_critic_score` should
    come from your actual retrieval system / a critic model, not be
    hand-typed (this file includes a naive placeholder so it runs
    standalone).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Check 1: Red-flag detection
# ---------------------------------------------------------------------------

# Each category maps to a set of phrases/keywords that indicate it.
# Keep these broad and biased toward over-triggering: a false positive
# here just means "be extra careful", a false negative could be harmful.
RED_FLAG_CATEGORIES: dict[str, list[str]] = {
    "difficulty_breathing": [
        r"can'?t breathe", r"cannot breathe", r"trouble breathing",
        r"difficulty breathing", r"shortness of breath", r"gasping for air",
        r"struggling to breathe", r"wheezing badly",
    ],
    "face_throat_swelling": [
        r"throat.{0,15}(swell|closing|tight)", r"face.{0,15}swell",
        r"lips.{0,15}swell", r"tongue.{0,15}swell",
        r"swelling.{0,15}(face|throat|lips|tongue)",
    ],
    "loss_of_consciousness": [
        r"passed out", r"lost consciousness", r"unresponsive",
        r"won'?t wake up", r"fainted", r"unconscious",
    ],
    "severe_chest_pain": [
        r"chest pain", r"chest tightness", r"pain (radiating|spreading) (down|to) (my |her |his )?arm",
        r"crushing (chest|pain)",
    ],
    "severe_allergic_reaction": [
        r"anaphyla", r"severe allergic reaction", r"hives.{0,15}(and|with).{0,15}(swell|breath)",
        r"allergic reaction.{0,20}(breath|swell|throat)",
    ],
}

_COMPILED_RED_FLAGS = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in RED_FLAG_CATEGORIES.items()
}


def detect_red_flags(text: str) -> list[str]:
    """Return the list of red-flag categories matched in `text`."""
    hits = []
    for category, patterns in _COMPILED_RED_FLAGS.items():
        if any(p.search(text) for p in patterns):
            hits.append(category)
    return hits


# ---------------------------------------------------------------------------
# Check 2: Confidence scoring
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceInputs:
    """The three signals that feed the final confidence score.

    Each should already be normalized to 0.0-1.0 by the upstream
    component that produces it (retriever, completeness checker,
    safety critic model, etc). Weights are tunable.
    """
    retrieval_relevance: float          # how well retrieved docs match the query
    completeness: float                 # does the answer cover dosage/interactions/warnings
    safety_critic_score: float          # a critic model's judgment of answer safety

    weight_retrieval: float = 0.35
    weight_completeness: float = 0.30
    weight_safety_critic: float = 0.35

    def final_confidence(self) -> float:
        total_weight = (
            self.weight_retrieval + self.weight_completeness + self.weight_safety_critic
        )
        score = (
            self.retrieval_relevance * self.weight_retrieval
            + self.completeness * self.weight_completeness
            + self.safety_critic_score * self.weight_safety_critic
        ) / total_weight
        return round(max(0.0, min(1.0, score)), 4)


def compute_confidence(inputs: ConfidenceInputs) -> float:
    """Returns a 0.0-1.0 confidence score."""
    return inputs.final_confidence()


# ---------------------------------------------------------------------------
# Check 3: Risk classification
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RiskThresholds:
    """Confidence cutoffs. Tune these against your eval set."""
    high_risk_below: float = 0.55     # confidence < this -> HIGH (do not answer)
    medium_risk_below: float = 0.80   # confidence < this -> MEDIUM (cautious guidance)
    # anything >= medium_risk_below -> LOW (answer)


def classify_risk(
    confidence: float,
    red_flags: list[str],
    thresholds: RiskThresholds = RiskThresholds(),
) -> RiskLevel:
    """Red flags always force HIGH risk regardless of confidence."""
    if red_flags:
        return RiskLevel.HIGH
    if confidence < thresholds.high_risk_below:
        return RiskLevel.HIGH
    if confidence < thresholds.medium_risk_below:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ---------------------------------------------------------------------------
# Orchestration: the full pipeline + the "highly visible" badge output
# ---------------------------------------------------------------------------

@dataclass
class GuardrailResult:
    risk_level: RiskLevel
    confidence: Optional[float]              # None when short-circuited by a red flag
    red_flags: list[str] = field(default_factory=list)
    action: str = ""
    badge_text: str = ""
    badge_color: str = ""                    # "green" | "yellow" | "red"
    answer_allowed: bool = True


def run_safety_pipeline(
    user_text: str,
    confidence_inputs: Optional[ConfidenceInputs] = None,
    thresholds: RiskThresholds = RiskThresholds(),
) -> GuardrailResult:
    """
    The full three-check pipeline.

    1. Red-flag detection runs first and can short-circuit everything
       else (STOP NORMAL RESPONSE -> EMERGENCY ESCALATION).
    2. If no red flags, confidence scoring runs.
    3. Confidence feeds risk classification, which decides the action
       and the badge shown to the user.
    """
    red_flags = detect_red_flags(user_text)

    if red_flags:
        return GuardrailResult(
            risk_level=RiskLevel.HIGH,
            confidence=None,
            red_flags=red_flags,
            action="EMERGENCY_ESCALATION",
            badge_text="Safety Escalation Triggered",
            badge_color="red",
            answer_allowed=False,
        )

    if confidence_inputs is None:
        # No signals available -> be conservative, treat as medium risk.
        confidence_inputs = ConfidenceInputs(0.5, 0.5, 0.5)

    confidence = compute_confidence(confidence_inputs)
    risk = classify_risk(confidence, red_flags, thresholds)

    if risk == RiskLevel.LOW:
        action = "ANSWER"
        badge_color = "green"
    elif risk == RiskLevel.MEDIUM:
        action = "CAUTIOUS_GUIDANCE_SEEK_PHARMACIST"
        badge_color = "yellow"
    else:
        action = "DO_NOT_ANSWER_ESCALATE"
        badge_color = "red"

    badge_text = (
        "Safety Escalation Triggered"
        if risk == RiskLevel.HIGH
        else f"Confidence: {int(round(confidence * 100))}%"
    )

    return GuardrailResult(
        risk_level=risk,
        confidence=confidence,
        red_flags=red_flags,
        action=action,
        badge_text=badge_text,
        badge_color=badge_color,
        answer_allowed=(risk != RiskLevel.HIGH),
    )


# ---------------------------------------------------------------------------
# Visible badge rendering (terminal version of the "highly visible" deliverable)
# ---------------------------------------------------------------------------

_ANSI = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "reset": "\033[0m",
    "dim": "\033[2m",
}

_DOT = {"green": "\u25cf", "yellow": "\u25cf", "red": "\u25cf"}  # ●


def render_badge_terminal(result: GuardrailResult) -> str:
    """Return a colored, pill-shaped badge string for terminal output."""
    color = _ANSI[result.badge_color]
    dot = _DOT[result.badge_color]
    reset = _ANSI["reset"]
    bold = _ANSI["bold"]
    return f"{color}{bold} {dot}  {result.badge_text} {reset}"


def print_full_result(user_text: str, result: GuardrailResult) -> None:
    print("-" * 72)
    print(f"{_ANSI['dim']}Input:{_ANSI['reset']} {user_text}")
    print(render_badge_terminal(result))
    print(f"  Risk level : {result.risk_level.value}")
    print(f"  Confidence : {result.confidence if result.confidence is not None else 'n/a (short-circuited)'}")
    print(f"  Red flags  : {result.red_flags or 'none'}")
    print(f"  Action     : {result.action}")
    print(f"  Answer OK? : {result.answer_allowed}")


# ---------------------------------------------------------------------------
# Demo / smoke test
# ---------------------------------------------------------------------------

_TEST_CASES = [
    (
        "What's the usual dose of ibuprofen for a headache?",
        ConfidenceInputs(retrieval_relevance=0.92, completeness=0.88, safety_critic_score=0.95),
    ),
    (
        "I took my medication and now my throat feels like it's closing and I can't breathe well",
        None,
    ),
    (
        "Can I take this new supplement with my blood thinner?",
        ConfidenceInputs(retrieval_relevance=0.55, completeness=0.40, safety_critic_score=0.60),
    ),
]


def run_smoke_test() -> None:
    for text, inputs in _TEST_CASES:
        result = run_safety_pipeline(text, inputs)
        print_full_result(text, result)


def run_interactive() -> None:
    """Type a message, optionally supply confidence signals, see the badge live."""
    print("Safety & Guardrail Lead — interactive demo")
    print("Type a message (or 'quit'). Leave signal prompts blank to use defaults (0.8).\n")
    while True:
        text = input(">> ").strip()
        if text.lower() in {"quit", "exit"}:
            break
        if not text:
            continue

        red_flags = detect_red_flags(text)
        inputs = None
        if not red_flags:
            def ask(prompt: str, default: float = 0.8) -> float:
                raw = input(f"   {prompt} [{default}]: ").strip()
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            rv = ask("retrieval relevance (0-1)")
            cp = ask("completeness (0-1)")
            sc = ask("safety critic score (0-1)")
            inputs = ConfidenceInputs(rv, cp, sc)

        result = run_safety_pipeline(text, inputs)
        print_full_result(text, result)
        print()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if "--interactive" in sys.argv or "-i" in sys.argv:
        run_interactive()
    else:
        run_smoke_test()
        print(f"\n{_ANSI['dim']}Tip: run with --interactive (or -i) to type your own messages.{_ANSI['reset']}")
