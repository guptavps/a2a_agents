import argparse
import asyncio
import os
from uuid import uuid4

import httpx
from a2a.client import create_client
from a2a.client.client import ClientConfig
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import TransportProtocol


_STATE_NAMES = {
    "1": "submitted",
    "2": "working",
    "3": "completed",
    "4": "failed",
    "5": "canceled",
    "6": "rejected",
    "7": "input required",
    "8": "auth required",
}


def _print_status(status) -> bool:
    state = getattr(status.state, "name", str(status.state))
    state = state.removeprefix("TASK_STATE_").lower()
    state = _STATE_NAMES.get(state, state)
    print(f"Task status: {state}")
    printed = True
    for part in getattr(getattr(status, "message", None), "parts", []) or []:
        if part.text:
            print(f"Agent: {part.text}")
    return printed


def print_response(response) -> bool:
    printed = False
    if response.HasField("message"):
        for part in response.message.parts:
            if part.text:
                print(f"Agent: {part.text}")
                printed = True
    if response.HasField("task"):
        task = response.task
        if task.status.message:
            printed = _print_status(task.status) or printed
        for artifact in task.artifacts:
            for part in artifact.parts:
                if part.text:
                    print(f"Agent: {part.text}")
                    printed = True
        if not task.status.message and not task.artifacts:
            printed = _print_status(task.status) or printed
    if response.HasField("status_update"):
        printed = _print_status(response.status_update.status) or printed
    if response.HasField("artifact_update"):
        for part in response.artifact_update.artifact.parts:
            if part.text:
                print(f"Agent: {part.text}")
                printed = True
    return printed


async def prompt_loop(server_url: str) -> None:
    client = await create_client(
        server_url,
        client_config=ClientConfig(
            supported_protocol_bindings=[TransportProtocol.JSONRPC],
            httpx_client=httpx.AsyncClient(timeout=120),
        ),
    )
    try:
        print(f"Connected to {server_url}. Enter 'exit' or 'quit' to stop.")
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
                    role=Role.ROLE_USER,
                    parts=[Part(text=prompt)],
                )
            )
            try:
                printed = False
                async for response in client.send_message(request):
                    printed = print_response(response) or printed
                if not printed:
                    print("Agent returned no text response.")
            except Exception as error:
                print(f"Request failed: {error}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send repeated prompts to the loan-closure A2A agent.")
    parser.add_argument(
        "--server-url",
        default=os.getenv("LOAN_CLOSURE_AGENT_URL", "http://localhost:8090"),
    )
    args = parser.parse_args()
    try:
        asyncio.run(prompt_loop(args.server_url))
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
