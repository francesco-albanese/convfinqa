from collections import Counter

from convfinqa.application.prompts.ab_selector import (
    AbConfig,
    AbVariant,
    parse_ab_config,
    resolve_served_label,
    select_label,
)


def test_disabled_config_serves_production() -> None:
    config = parse_ab_config({"enabled": False})

    assert select_label(config, "user-1") == "production"


def test_absent_config_serves_production() -> None:
    assert select_label(parse_ab_config(None), "user-1") == "production"


def test_same_user_always_gets_the_same_variant() -> None:
    config = AbConfig(
        enabled=True,
        variants=(AbVariant("production", 50), AbVariant("git-abc123", 50)),
    )

    first = select_label(config, "user-42")
    second = select_label(config, "user-42")

    assert first == second


def test_different_users_can_get_different_variants() -> None:
    config = AbConfig(
        enabled=True,
        variants=(AbVariant("production", 50), AbVariant("git-abc123", 50)),
    )

    labels = {select_label(config, f"user-{i}") for i in range(50)}

    assert labels == {"production", "git-abc123"}


def test_distribution_approximates_configured_weights() -> None:
    config = AbConfig(
        enabled=True,
        variants=(AbVariant("production", 90), AbVariant("git-abc123", 10)),
    )

    counts = Counter(select_label(config, f"user-{i}") for i in range(5000))
    production_share = counts["production"] / 5000

    assert 0.85 <= production_share <= 0.95


def test_malformed_config_missing_variants_serves_production() -> None:
    config = parse_ab_config({"enabled": True})

    assert select_label(config, "user-1") == "production"


def test_malformed_config_zero_weight_serves_production() -> None:
    config = parse_ab_config(
        {"enabled": True, "variants": [{"label": "git-abc123", "weight": 0}]}
    )

    assert select_label(config, "user-1") == "production"


def test_malformed_config_wrong_type_serves_production() -> None:
    assert parse_ab_config("not-a-dict") is None
    assert parse_ab_config({"enabled": "yes"}) is None
    assert (
        parse_ab_config(
            {"enabled": True, "variants": [{"label": "x", "weight": "heavy"}]}
        )
        is None
    )


def test_parse_ab_config_accepts_well_formed_block() -> None:
    config = parse_ab_config(
        {
            "enabled": True,
            "variants": [
                {"label": "production", "weight": 80},
                {"label": "git-abc123", "weight": 20},
            ],
        }
    )

    assert config is not None
    assert config.enabled is True
    assert config.variants == (
        AbVariant("production", 80.0),
        AbVariant("git-abc123", 20.0),
    )


def test_resolve_served_label_reports_no_malformed_flag_when_absent() -> None:
    label, malformed = resolve_served_label(None, "user-1")

    assert label == "production"
    assert malformed is False


def test_resolve_served_label_reports_no_malformed_flag_when_disabled() -> None:
    label, malformed = resolve_served_label({"enabled": False}, "user-1")

    assert label == "production"
    assert malformed is False


def test_resolve_served_label_flags_malformed_config_and_serves_production() -> None:
    label, malformed = resolve_served_label({"enabled": True}, "user-1")

    assert label == "production"
    assert malformed is True


def test_resolve_served_label_selects_enabled_variant() -> None:
    label, malformed = resolve_served_label(
        {
            "enabled": True,
            "variants": [{"label": "git-abc123", "weight": 100}],
        },
        "user-1",
    )

    assert label == "git-abc123"
    assert malformed is False
