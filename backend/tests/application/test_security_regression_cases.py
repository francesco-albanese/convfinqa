from convfinqa.application.security_regression_cases import (
    REPRESENTATIVE_CASES,
    AttackCategory,
)


def test_representative_cases_cover_every_attack_category() -> None:
    categories = {case.category for case in REPRESENTATIVE_CASES}
    assert categories == set(AttackCategory)


def test_representative_cases_have_unique_ids_and_at_least_one_turn() -> None:
    ids = [case.id for case in REPRESENTATIVE_CASES]
    assert len(ids) == len(set(ids))
    assert all(case.turns for case in REPRESENTATIVE_CASES)
