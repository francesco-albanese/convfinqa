# convfinqa

ConvFinQA is a local-first conversational financial QA application over the
ConvFinQA dataset. It provides a FastAPI streaming backend, React/Vite UI,
PostgreSQL persistence, and Bedrock inference through LiteLLM.

## Run locally

```bash
make up
```

Open <http://localhost:5173>. The application and authentication run locally;
Bedrock uses your existing AWS profile in `eu-west-2` for inference only. No AWS
infrastructure is deployed. See [the local run guide](./docs/how-to-run-the-app.md).

## Dataset

The [ConvFinQA dataset](./data/convfinqa_dataset.json) contains roughly 3,900
multi-turn dialogues over semi-structured financial documents. Questions often
require chained numerical reasoning across tables and narrative text.

## Stack

- Python 3.13, FastAPI, SQLAlchemy, PostgreSQL
- React 19, Vite, TypeScript
- LiteLLM behind a hexagonal `LLMPort`
- Pytest, Vitest, and Playwright

The system follows [hexagonal architecture](./docs/hexagonal.md).
