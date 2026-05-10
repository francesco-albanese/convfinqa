- the wheel ships `backend/src/convfinqa` as the installed package `convfinqa` (see
  `[tool.hatch.build.targets.wheel] packages = ["backend/src/convfinqa"]`), so imports
  MUST be rooted at the package name, NOT the `backend/src/` directory. Do NOT do
  `from backend.src.convfinqa.application.use_cases.send_message import ...` (only
  works under pytest's `pythonpath`, breaks `uv run main` and any installed
  entry point). DO this:
  `from convfinqa.application.use_cases.send_message import ...`
- never use relative imports across packages
  (e.g. `from ...application.use_cases.send_message import ...`)
