# convfinqa

ConvFinQA is a chatbot application that sends user's questions to an LLM, loads the relevant document into the context and returns a response related to the context provided.

## Brief context of original ConvFinQA

ConvFinQA is a benchmark dataset of ~3,900 multi-turn conversational Q&A dialogues over semi-structured financial documents, requiring chained numerical reasoning across turns to answer questions like percentage changes, sums, and comparisons derived from earnings reports.

Earlier work on the [dataset](./data/convfinqa_dataset.json) used an intra document retriever to select relevant sentences and table rows before passing them to the model. This constraint was necessary due to the much smaller context window of models available at that time.

Modern LLMs have a context window size that allows for the full document to be loaded in the context window, without any chunking, which should simplify the overall logic and improve the accuracy of responses.

## CLI + UI

The app provides both a CLI and a simple UI to chat with the LLM. It requires populating ENV variables for chatting. [.env file based on the .env.example](./.env.example)

## Tech stack

- python 3.13+
- `uv` package manager
- LiteLLM used as an LLM router to quickly switch to different model providers with a unified structure
- Pydantic validation and tools
- FastAPI with streaming
- `typer` CLI
- `Next.js` typescript app for the UI

## Software architecture

The system is implemented with [hexagonal architecture](./docs/hexagonal.md)