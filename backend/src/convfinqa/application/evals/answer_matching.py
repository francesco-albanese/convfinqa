import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class AnswerMatchResult:
    passed: bool
    score: float


@dataclass(frozen=True, slots=True)
class _ParsedAnswer:
    value: Decimal
    is_percent: bool
    decimals: int


def score_answer(model_answer: str, gold_answer: str) -> AnswerMatchResult:
    gold = _parse_answer(gold_answer)
    model = _parse_answer(model_answer)
    if gold is None or model is None:
        return AnswerMatchResult(passed=False, score=0.0)

    quant = _quantizer(gold.decimals)
    gold_value = gold.value.quantize(quant, rounding=ROUND_HALF_UP)
    candidates = [model.value]
    if gold.is_percent and not model.is_percent:
        candidates.append(model.value * Decimal(100))

    passed = any(
        candidate.quantize(quant, rounding=ROUND_HALF_UP) == gold_value
        for candidate in candidates
    )
    return AnswerMatchResult(passed=passed, score=1.0 if passed else 0.0)


_NUMBER_RE = re.compile(
    r"(?P<number>[-+]?(?:\d+(?:,\d{3})*|\d*)(?:\.\d+)?)(?P<percent>\s*%)?"
)


def _parse_answer(answer: str) -> _ParsedAnswer | None:
    normalized = answer.strip().strip("\"'").replace("$", "")
    for match in _NUMBER_RE.finditer(normalized):
        raw_number = match.group("number")
        if raw_number in {"", "+", "-", ".", "+.", "-."}:
            continue
        cleaned = raw_number.replace(",", "")
        if cleaned.startswith("."):
            cleaned = f"0{cleaned}"
        elif cleaned.startswith("-."):
            cleaned = cleaned.replace("-.", "-0.", 1)
        elif cleaned.startswith("+."):
            cleaned = cleaned.replace("+.", "+0.", 1)
        try:
            value = Decimal(cleaned)
        except InvalidOperation:
            continue
        return _ParsedAnswer(
            value=value,
            is_percent=bool(match.group("percent")),
            decimals=_decimal_places(raw_number),
        )
    return None


def _decimal_places(raw_number: str) -> int:
    without_commas = raw_number.replace(",", "")
    if "." not in without_commas:
        return 0
    return len(without_commas.rsplit(".", 1)[1])


def _quantizer(decimals: int) -> Decimal:
    if decimals <= 0:
        return Decimal("1")
    return Decimal("1").scaleb(-decimals)
