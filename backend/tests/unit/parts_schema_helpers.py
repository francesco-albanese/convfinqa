import json

from convfinqa.application.parts_schema import ENVELOPE_MAX_BYTES, build_envelope


def envelope_parts_size(parts: list[dict[str, object]]) -> int:
    return len(json.dumps(parts, separators=(",", ":")).encode("utf-8"))


def build_oversized_text_parts(chunk_count: int = 6) -> list[dict[str, object]]:
    chunk_size = ENVELOPE_MAX_BYTES // 4
    large_content = "z" * chunk_size
    return [{"kind": "text", "content": large_content} for _ in range(chunk_count)]


def build_and_measure_parts(parts: list[dict[str, object]]) -> tuple[int, int]:
    result = build_envelope(parts)
    return len(result["parts"]), envelope_parts_size(result["parts"])
