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
        r"lips?.{0,15}swell", r"tongue.{0,15}swell",
        r"swelling.{0,15}(face|throat|lips?|tongue)",
        r"swollen (throat|tongue|lips?|face)",
    ],
    "loss_of_consciousness": [
        r"passed out", r"lost consciousness", r"unresponsive",
        r"won'?t wake up", r"fainted", r"unconscious", r"collapsed",
    ],
    "severe_chest_pain": [
        r"chest pain", r"chest tightness", r"pain (radiating|spreading) (down|to) (my |her |his )?arm",
        r"crushing (chest|pain)", r"heart attack",
    ],
    "severe_allergic_reaction": [
        r"anaphyla", r"severe allergic reaction", r"hives.{0,15}(and|with).{0,15}(swell|breath)",
        r"allergic reaction.{0,20}(breath|swell|throat)",
    ],
    "internal_bleeding": [
        r"vomit(ing|ed)? blood", r"blood in vomit", r"coffee[- ]ground",
        r"black (tarry )?stool", r"blood in stool", r"rectal bleed(ing)?",
        r"cough(ing)? up blood",
    ],
    "stroke_symptoms": [
        r"facial droop", r"face droop", r"slurred speech", r"speech slurred",
        r"thunderclap headache", r"sudden (numbness|weakness)",
    ],
    "acute_overdose_poisoning": [
        r"\boverdose\b", r"swallowed (the |a )?(whole|entire) bottle",
        r"took (the |a )?(whole|entire) bottle", r"drank poison",
        r"took too many pills", r"swallowed excessive",
    ],
    "seizures_convulsions": [
        r"\bseizure\b", r"\bconvulsion\b", r"\bfits\b",
    ],
    "self_harm_crisis": [
        r"kill myself", r"end my life", r"\bsuicid",
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
# Check 1B: Toxic Dosage & Overdose Quantity Detection
# ---------------------------------------------------------------------------

def detect_toxic_dosage(text: str) -> Optional[dict]:
    """
    Detect explicit queries or reports of dangerously excessive or toxic doses.
    Returns details if toxic threshold is breached, else None.
    """
    lowered = text.lower()

    # Match numeric milligram / gram doses (e.g., '10000mg', '10,000 mg', '5 g', '8 grams')
    dose_matches = re.findall(r"(\d[\d,]*)\s*(mg|milligrams?|g|grams?)\b", lowered)
    for amount_str, unit in dose_matches:
        try:
            val = float(amount_str.replace(",", ""))
            mg_val = val * 1000 if unit.startswith("g") else val
        except ValueError:
            continue

        # Acetaminophen / Paracetamol toxic limits (>4000 mg/day or >1000 mg single dose query)
        is_apap = any(k in lowered for k in ["paracetamol", "acetaminophen", "tylenol"])
        if is_apap and mg_val >= 4000:
            return {
                "is_toxic": True,
                "dosage_mg": mg_val,
                "reason": (
                    f"Reported dose ({int(mg_val)} mg) reaches or exceeds the absolute 24-hour maximum "
                    "adult limit for acetaminophen (4,000 mg). Single doses of this magnitude can cause "
                    "severe, irreversible liver injury or acute liver failure."
                )
            }

        # Ibuprofen toxic limits (>3200 mg/day or >=3200 mg query)
        is_ibup = any(k in lowered for k in ["ibuprofen", "advil", "motrin", "nsaid"])
        if is_ibup and mg_val >= 3200:
            return {
                "is_toxic": True,
                "dosage_mg": mg_val,
                "reason": (
                    f"Reported dose ({int(mg_val)} mg) exceeds the maximum clinical threshold "
                    "for ibuprofen (1,200 mg/day OTC, 3,200 mg/day prescription maximum). "
                    "Severe risk of acute renal failure and massive gastrointestinal hemorrhage."
                )
            }

        # Unspecified drug massive dose (>= 5,000 mg)
        if mg_val >= 5000:
            return {
                "is_toxic": True,
                "dosage_mg": mg_val,
                "reason": (
                    f"Extremely high single/daily dosage ({int(mg_val)} mg) detected. "
                    "High risk of acute systemic toxicity or overdose."
                )
            }

    # Match pill counts (e.g., 'took 15 pills', 'swallowed 12 tablets')
    pill_match = re.search(r"(?:take|took|swallow(?:ed)?)\s+(\d{2,})\s*(?:pills|tablets|capsules)", lowered)
    if pill_match:
        count = int(pill_match.group(1))
        if count >= 8:
            return {
                "is_toxic": True,
                "pill_count": count,
                "reason": (
                    f"Excessive pill quantity ({count} tablets/capsules) reported. "
                    "Immediate risk of acute drug toxicity."
                )
            }

    return None


# ---------------------------------------------------------------------------
# Check 1C: Vulnerable Population Safety Filter (Pediatric, Pregnancy, Organ Impairment)
# ---------------------------------------------------------------------------

_PEDIATRIC_PATTERN = re.compile(
    r"\b(?:child(?:ren)?|infant|toddler|baby|babies|newborn|pediatric|"
    r"[1-9]\s*(?:year|yr)s?[\s-]old|1[0-2]\s*(?:year|yr)s?[\s-]old|\d+\s*(?:month|mo)s?[\s-]old)\b",
    re.IGNORECASE
)

_PREGNANCY_PATTERN = re.compile(
    r"\b(?:pregnant|pregnancy|trimester|breastfeed(?:ing)?|nursing|lactat(?:ing|ion)|unborn (?:baby|child))\b",
    re.IGNORECASE
)

_ORGAN_IMPAIRMENT_PATTERN = re.compile(
    r"\b(?:kidney (?:disease|failure|damage|impairment)|renal (?:disease|failure|impairment)|"
    r"liver (?:disease|failure|cirrhosis|damage)|hepatic impairment)\b",
    re.IGNORECASE
)


def detect_vulnerable_populations(text: str) -> list[dict]:
    """
    Detect special populations where standard adult OTC dosage rules are dangerous
    or strictly contraindicated without specialist oversight.
    """
    warnings = []

    if _PEDIATRIC_PATTERN.search(text):
        warnings.append({
            "population": "pediatric",
            "severity": "high",
            "message": (
                "Pediatric patient context detected (child/infant). Adult OTC dosing guidelines "
                "must NEVER be applied to children. Pediatric dosages require exact weight-based "
                "calculations (mg/kg) under pediatric guidance."
            )
        })

    if _PREGNANCY_PATTERN.search(text):
        warnings.append({
            "population": "pregnancy_lactation",
            "severity": "high",
            "message": (
                "Pregnancy or lactation context detected. Many common medications (including NSAIDs "
                "in the third trimester) carry FDA black-box warnings for fetal harm or pass into breast milk."
            )
        })

    if _ORGAN_IMPAIRMENT_PATTERN.search(text):
        warnings.append({
            "population": "organ_impairment",
            "severity": "caution",
            "message": (
                "Renal or hepatic impairment reported. Clearance of medications may be severely compromised, "
                "requiring clinical dose titration and monitoring."
            )
        })

    return warnings


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
    vulnerable_warnings: list[str] = field(default_factory=list)
    toxic_dose_info: Optional[dict] = None


def run_safety_pipeline(
    user_text: str,
    confidence_inputs: Optional[ConfidenceInputs] = None,
    thresholds: RiskThresholds = RiskThresholds(),
) -> GuardrailResult:
    """
    The full safety guardrail pipeline.

    1. Red-flag detection runs first -> immediate emergency override.
    2. Toxic dosage detection runs -> immediate emergency override.
    3. Vulnerable population checks (pediatric, pregnancy) -> clinical escalation.
    4. Confidence scoring feeds risk classification.
    """
    red_flags = detect_red_flags(user_text)
    toxic_dose = detect_toxic_dosage(user_text)
    vulnerable_pops = detect_vulnerable_populations(user_text)
    pop_messages = [p["message"] for p in vulnerable_pops]

    if red_flags:
        return GuardrailResult(
            risk_level=RiskLevel.HIGH,
            confidence=None,
            red_flags=red_flags,
            action="EMERGENCY_ESCALATION",
            badge_text="Safety Escalation Triggered",
            badge_color="red",
            answer_allowed=False,
            vulnerable_warnings=pop_messages,
            toxic_dose_info=toxic_dose,
        )

    if toxic_dose:
        return GuardrailResult(
            risk_level=RiskLevel.HIGH,
            confidence=None,
            red_flags=["toxic_dosage_overdose"],
            action="EMERGENCY_ESCALATION",
            badge_text="Toxic / Lethal Dose Alert",
            badge_color="red",
            answer_allowed=False,
            vulnerable_warnings=pop_messages,
            toxic_dose_info=toxic_dose,
        )

    # If pediatric or pregnancy detected, standard adult RAG OTC guidance is strictly blocked
    has_high_risk_pop = any(p["severity"] == "high" for p in vulnerable_pops)
    if has_high_risk_pop:
        return GuardrailResult(
            risk_level=RiskLevel.HIGH,
            confidence=0.30,
            red_flags=[],
            action="SPECIAL_POPULATION_ESCALATE",
            badge_text="Special Population Review Required",
            badge_color="yellow",
            answer_allowed=False,
            vulnerable_warnings=pop_messages,
            toxic_dose_info=None,
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
        vulnerable_warnings=pop_messages,
        toxic_dose_info=None,
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
