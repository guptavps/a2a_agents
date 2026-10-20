import argparse
import asyncio
import json
import os
from uuid import uuid4

import httpx
from a2a.client import create_client
from a2a.client.client import ClientConfig
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import TransportProtocol

def _is_intent_decision_payload(text: str) -> bool:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and {
        "intent",
        "confidence",
        "rationale",
    }.issubset(payload)


def _print_response(response, printed_texts: set[str]) -> bool:
    response_parts = []
    if response.HasField("message"):
        response_parts.extend(response.message.parts)
    if response.HasField("task"):
        task = response.task
        if task.status.message:
            response_parts.extend(task.status.message.parts)
        for artifact in task.artifacts:
            response_parts.extend(artifact.parts)
    if response.HasField("status_update"):
        status = response.status_update.status
        if status.message:
            response_parts.extend(status.message.parts)
    if response.HasField("artifact_update"):
        response_parts.extend(response.artifact_update.artifact.parts)

    printed = False
    for part in response_parts:
        text = part.text
        if not text or text in printed_texts or _is_intent_decision_payload(text):
            continue
        print(f"Agent: {text}")
        printed_texts.add(text)
        printed = True
    return printed


async def prompt_loop(server_url: str, context_id: str) -> None:
    client = await create_client(
        server_url,
        client_config=ClientConfig(
            supported_protocol_bindings=[TransportProtocol.JSONRPC],
            httpx_client=httpx.AsyncClient(timeout=120),
        ),
    )
    try:
        print(f"Connected to {server_url}.")
        print(f"Conversation context_id: {context_id}")
        print("Reuse this context_id with --context-id to continue the same session later.")
        print("Enter 'exit' or 'quit' to stop.")
        while True:
            try:
                prompt = input("You: ").strip()
            except EOFError:
                break
            if prompt.lower() in {"exit", "quit"}:
                break
            if not prompt:
                continue

            request = SendMessageRequest(
                message=Message(
                    message_id=str(uuid4()),
                    context_id=context_id,
                    role=Role.ROLE_USER,
                    parts=[Part(text=prompt)],
                )
            )
            try:
                printed = False
                printed_texts: set[str] = set()
                async for response in client.send_message(request):
                    printed = _print_response(response, printed_texts) or printed
                if not printed:
                    print("Agent returned no text response.")
            except Exception as error:
                print(f"Request failed: {error}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send repeated prompts to the workflow A2A server.")
    parser.add_argument(
        "--server-url",
        default=os.getenv("INTENT_DETECTOR_AGENT_URL", "http://localhost:8092"),
    )
    parser.add_argument(
        "--context-id",
        default=os.getenv("INTENT_DETECTOR_CONTEXT_ID") or str(uuid4()),
        help="Stable conversation context ID. Reuse to preserve A2A/ADK session history across runs.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(prompt_loop(args.server_url, args.context_id))
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
