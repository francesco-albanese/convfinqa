import re
from collections.abc import Mapping
from importlib import resources


class LocalFilePromptProvider:
    def __init__(self, package: str = "convfinqa.adapters.prompts.catalog") -> None:
        self._package = package

    def compile(self, name: str, label: str, variables: Mapping[str, object]) -> str:
        template = self._load_template(name, label)
        return compile_prompt_template(template, variables)

    def _load_template(self, name: str, label: str) -> str:
        filename = f"{name}.{label}.md"
        try:
            return (
                resources.files(self._package)
                .joinpath(filename)
                .read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise ValueError(f"prompt not found: {name}@{label}") from exc


_PLACEHOLDER = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def compile_prompt_template(template: str, variables: Mapping[str, object]) -> str:
    used: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise ValueError(f"missing prompt variable: {key}")
        used.add(key)
        return str(variables[key])

    compiled = _PLACEHOLDER.sub(replace, template)
    unused = set(variables).difference(used)
    if unused:
        raise ValueError(f"unused prompt variables: {', '.join(sorted(unused))}")
    return compiled
