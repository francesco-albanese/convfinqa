import hashlib
from dataclasses import dataclass
from typing import Any, cast

DEFAULT_LABEL = "production"
_BUCKET_RESOLUTION = 10_000


@dataclass(frozen=True, slots=True)
class AbVariant:
    label: str
    weight: float


@dataclass(frozen=True, slots=True)
class AbConfig:
    enabled: bool
    variants: tuple[AbVariant, ...] = ()


def parse_ab_config(raw: object) -> AbConfig | None:
    """Parses a prompt's config.ab block. Returns None if malformed, so the
    caller can fall back to serving `production` rather than raising."""
    if raw is None:
        return AbConfig(enabled=False)
    if not isinstance(raw, dict):
        return None
    config = cast("dict[str, Any]", raw)

    enabled = config.get("enabled", False)
    if not isinstance(enabled, bool):
        return None
    if not enabled:
        return AbConfig(enabled=False)

    raw_variants = config.get("variants")
    if not isinstance(raw_variants, list) or not raw_variants:
        return None
    typed_variants = cast("list[Any]", raw_variants)

    variants: list[AbVariant] = []
    for raw_variant in typed_variants:
        if not isinstance(raw_variant, dict):
            return None
        variant = cast("dict[str, Any]", raw_variant)
        label = variant.get("label")
        weight = variant.get("weight")
        if not isinstance(label, str) or not label:
            return None
        if isinstance(weight, bool) or not isinstance(weight, int | float):
            return None
        if weight <= 0:
            return None
        variants.append(AbVariant(label=label, weight=float(weight)))

    if sum(variant.weight for variant in variants) <= 0:
        return None

    return AbConfig(enabled=True, variants=tuple(variants))


def select_label(
    ab_config: AbConfig | None,
    bucket_key: str,
    default_label: str = DEFAULT_LABEL,
) -> str:
    if ab_config is None or not ab_config.enabled or not ab_config.variants:
        return default_label

    total_weight = sum(variant.weight for variant in ab_config.variants)
    digest = hashlib.sha256(bucket_key.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % _BUCKET_RESOLUTION
    position = (bucket / _BUCKET_RESOLUTION) * total_weight

    cumulative = 0.0
    for variant in ab_config.variants:
        cumulative += variant.weight
        if position < cumulative:
            return variant.label
    return ab_config.variants[-1].label


def resolve_served_label(
    raw_ab_config: object,
    bucket_key: str,
    default_label: str = DEFAULT_LABEL,
) -> tuple[str, bool]:
    """Decides which label to serve for a request.

    Returns (label, was_malformed). `was_malformed` is True only when
    `raw_ab_config` was present but failed validation - callers use it to log
    a warning, since a genuinely absent or disabled block is not an error.
    """
    ab_config = parse_ab_config(raw_ab_config)
    malformed = ab_config is None and raw_ab_config is not None
    return select_label(ab_config, bucket_key, default_label), malformed
