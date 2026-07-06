import pytest

from convfinqa.adapters.prompts.local_file import (
    LocalFilePromptProvider,
    compile_prompt_template,
)


async def test_local_prompt_provider_resolves_catalog_prompt() -> None:
    compiled = await LocalFilePromptProvider().compile(
        "convfinqa-system",
        "production",
        {
            "title": "ACME",
            "ticker": "ACME",
            "year": 2024,
            "page": 1,
            "pre_text": "pre",
            "post_text": "post",
            "tool_docs": "## tool docs",
        },
    )

    assert compiled.text.startswith("<trusted_application_policy>")
    assert "You are ConvFinQA" in compiled.text
    assert "Title: ACME" in compiled.text
    assert "## tool docs" in compiled.text
    assert compiled.version is None


def test_prompt_template_compile_replaces_all_variables() -> None:
    compiled = compile_prompt_template(
        "Hello {{ name }} from {{place}}.", {"name": "ConvFinQA", "place": "tests"}
    )

    assert compiled == "Hello ConvFinQA from tests."


def test_prompt_template_compile_fails_on_missing_variable() -> None:
    with pytest.raises(ValueError, match="missing prompt variable: missing"):
        compile_prompt_template("Hello {{missing}}.", {})


def test_prompt_template_compile_fails_on_unused_variable() -> None:
    with pytest.raises(ValueError, match="unused prompt variables: extra"):
        compile_prompt_template("Hello {{name}}.", {"name": "ConvFinQA", "extra": "x"})


async def test_local_prompt_provider_fails_on_missing_prompt() -> None:
    with pytest.raises(ValueError, match="prompt not found: missing@production"):
        await LocalFilePromptProvider().compile("missing", "production", {})


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("../../../../../../etc/passwd", "production"),
        ("convfinqa-system", "../../../../../../etc/passwd"),
        ("convfinqa-system/../../secret", "production"),
        ("convfinqa-system", "production/../../secret"),
    ],
)
async def test_local_prompt_provider_rejects_path_traversal(
    name: str, label: str
) -> None:
    with pytest.raises(ValueError, match="prompt not found"):
        await LocalFilePromptProvider().compile(name, label, {})
