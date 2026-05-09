- you have `pythonpath = ["."]` in pyproject.toml, which means that imports can
  always be absolute to the root, for example DO NOT do this
  `from ...application.use_cases.send_message import SendMessageUseCase`
  but do this instead `from src.convfinqa.application.use_cases.send_message import ...`
