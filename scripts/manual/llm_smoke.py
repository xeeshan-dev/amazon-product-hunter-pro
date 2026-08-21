"""Manual smoke test for the optional LLM assistant.

Requires GROQ_API_KEY. This script is intentionally excluded from pytest.
"""
import argparse
import asyncio

from web_app.backend.services.llm_service import LLMService


async def run(prompt: str) -> None:
    service = LLMService()
    response = await service.get_chat_response([{"role": "user", "content": prompt}])
    print(response)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt",
        default="What are the most important metrics in Amazon product research?",
    )
    args = parser.parse_args()
    asyncio.run(run(args.prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
