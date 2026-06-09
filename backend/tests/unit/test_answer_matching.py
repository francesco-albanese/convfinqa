import pytest

from convfinqa.application.evals.answer_matching import score_answer


@pytest.mark.parametrize(
    "gold",
    ["39%", "26%", "186", "177", "9", "5.1%", "2.6", "2.2", ".4", "18%"],
)
def test_canonical_gold_answers_match_exact_values(gold: str) -> None:
    result = score_answer(gold, gold)

    assert result.passed is True
    assert result.score == 1.0


@pytest.mark.parametrize(
    ("model", "gold"),
    [
        ("18", "18%"),
        ("18.0", "18%"),
        ("0.18", "18%"),
        ("5.1", "5.1%"),
        ("0.051", "5.1%"),
        ("5.1%", "5.1%"),
    ],
)
def test_percent_gold_matches_displayed_value_or_bare_fraction(
    model: str, gold: str
) -> None:
    assert score_answer(model, gold).passed is True


@pytest.mark.parametrize(
    ("model", "gold"),
    [
        ("2.64", "2.6"),
        ("2.24", "2.2"),
        ("0.4", ".4"),
        (".4", ".4"),
    ],
)
def test_model_answer_rounds_to_gold_display_precision(model: str, gold: str) -> None:
    assert score_answer(model, gold).passed is True


@pytest.mark.parametrize(
    ("model", "gold"),
    [
        ("2.65", "2.6"),
        ("2.3", "2.2"),
        ("0.052", "5.1%"),
        ("19", "18%"),
    ],
)
def test_wrong_figure_fails(model: str, gold: str) -> None:
    result = score_answer(model, gold)

    assert result.passed is False
    assert result.score == 0.0


@pytest.mark.parametrize(
    ("model", "gold"),
    [
        (" $1,860 ", "1860"),
        ('"177"', "177"),
        ("The answer is $181,001 thousand.", "181001"),
        ("Net change: 9.", "9"),
    ],
)
def test_normalizes_currency_commas_quotes_and_prose(model: str, gold: str) -> None:
    assert score_answer(model, gold).passed is True


@pytest.mark.parametrize(
    "model",
    ["no numeric answer", "", "not available"],
)
def test_non_numeric_model_answer_fails(model: str) -> None:
    assert score_answer(model, "18%").passed is False
