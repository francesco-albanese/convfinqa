import pytest
from pydantic import ValidationError

from convfinqa.application.agent.tools.math import (
    MathInput,
    add,
    divide,
    greater_than,
    multiply,
    subtract,
)

# --- add ---


def test_add_two_positive_integers() -> None:
    assert add(a="206588", b="181001") == {"result": "387589"}


def test_add_negative_numbers() -> None:
    result = add(a="-50", b="-30")
    assert result == {"result": "-80"}


def test_add_positive_and_negative() -> None:
    result = add(a="100", b="-40")
    assert result == {"result": "60"}


def test_add_preserves_decimal_precision_for_large_numbers() -> None:
    a = "9" * 25
    b = "1"
    result = add(a=a, b=b)
    expected = str(int(a) + 1)
    assert result == {"result": expected}


# --- subtract ---


def test_subtract_basic() -> None:
    assert subtract(a="206588", b="181001") == {"result": "25587"}


def test_subtract_yields_negative_result() -> None:
    result = subtract(a="10", b="50")
    assert result == {"result": "-40"}


def test_subtract_decimals() -> None:
    result = subtract(a="3.14", b="1.14")
    assert result["result"] == "2.00"


# --- multiply ---


def test_multiply_integers() -> None:
    assert multiply(a="3", b="7") == {"result": "21"}


def test_multiply_by_zero() -> None:
    assert multiply(a="12345", b="0") == {"result": "0"}


def test_multiply_decimals() -> None:
    result = multiply(a="3.14", b="100")
    assert result == {"result": "314.00"}


def test_multiply_negative_by_positive() -> None:
    result = multiply(a="-5", b="6")
    assert result == {"result": "-30"}


# --- divide ---


def test_divide_even() -> None:
    result = divide(a="100", b="4")
    assert result == {"result": "25"}


def test_divide_produces_decimal() -> None:
    result = divide(a="387589", b="2")
    assert result == {"result": "193794.5"}


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ValueError, match="division by zero"):
        divide(a="100", b="0")


def test_divide_negative_numerator() -> None:
    result = divide(a="-90", b="3")
    assert result == {"result": "-30"}


def test_divide_preserves_28_sig_figs() -> None:
    result = divide(a="1", b="3")
    # Decimal prec=28 yields exactly 28 significant figures for a repeating decimal
    assert result == {"result": "0.3333333333333333333333333333"}


# --- greater_than ---


def test_greater_than_when_a_is_larger() -> None:
    assert greater_than(a="206588", b="181001") == {"result": "true"}


def test_greater_than_when_a_is_smaller() -> None:
    assert greater_than(a="1", b="5") == {"result": "false"}


def test_greater_than_equal_values_returns_false() -> None:
    assert greater_than(a="42", b="42") == {"result": "false"}


def test_greater_than_negative_numbers() -> None:
    assert greater_than(a="-1", b="-5") == {"result": "true"}


def test_greater_than_decimal_comparison() -> None:
    assert greater_than(a="3.15", b="3.14") == {"result": "true"}


# --- MathInput validation ---


def test_non_numeric_string_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a="abc", b="1")


def test_nan_string_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a="nan", b="1")


def test_inf_string_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a="inf", b="1")


def test_scientific_notation_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a="1e10", b="2")


def test_leading_plus_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a="+5", b="2")


def test_leading_dot_rejected() -> None:
    with pytest.raises(ValidationError):
        MathInput(a=".5", b="2")


def test_valid_negative_decimal_accepted() -> None:
    m = MathInput(a="-3.14", b="2.72")
    assert m.a == "-3.14"
    assert m.b == "2.72"
