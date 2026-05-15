FROM public.ecr.aws/lambda/python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml .
RUN uv pip install --no-cache pg8000

COPY handler.py ${LAMBDA_TASK_ROOT}/
CMD ["handler.handler"]
