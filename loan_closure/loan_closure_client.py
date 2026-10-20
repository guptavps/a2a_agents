import argparse
import asyncio
import os
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from a2a.client import create_client
from a2a.client.client import ClientConfig
from a2a.client.errors import A2AClientTimeoutError
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import TransportProtocol

load_dotenv()

DEFAULT_SERVER_URL = "http://34.9.158.18:8090"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120.0


async def send_loan_closure_request(
    prompt: str,
    client,
) -> None:
    """Send one prompt and print the A2A response events."""
    request = SendMessageRequest(
        message=Message(
            message_id=str(uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text=prompt)],
        )
    )

    async for response in client.send_message(request):
        if response.HasField("task"):
            task = response.task
            if task.status.message.parts:
                for part in task.status.message.parts:
                    if part.text:
                        print(part.text)
            elif task.artifacts:
                for artifact in task.artifacts:
                    for part in artifact.parts:
                        if part.text:
                            print(part.text)
            else:
                print(f"Task status: {task.status.state}")
        if response.HasField("message"):
            for part in response.message.parts:
                if part.text:
                    print(part.text)
        if response.HasField("status_update"):
            print(f"Task status: {response.status_update.status.state}")
        if response.HasField("artifact_update"):
            for part in response.artifact_update.artifact.parts:
                if part.text:
                    print(part.text)


async def run_prompt_loop(server_url: str | None = None) -> None:
    """Keep sending prompts until the user exits."""
    base_url = server_url or os.getenv("LOAN_CLOSURE_AGENT_URL", DEFAULT_SERVER_URL)
    timeout_seconds = float(
        os.getenv("LOAN_CLOSURE_CLIENT_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    client = await create_client(
        base_url,
        client_config=ClientConfig(
            supported_protocol_bindings=[TransportProtocol.HTTP_JSON],
            httpx_client=httpx.AsyncClient(timeout=timeout_seconds),
        ),
    )

    try:
        print("Connected to loan closure agent. Type 'exit' to quit.")
        while True:
            try:
                prompt = input("You: ").strip()
            except EOFError:
                print()
                break

            if prompt.lower() in {"exit", "quit"}:
                break
            if not prompt:
                continue

            try:
                await send_loan_closure_request(prompt, client)
            except A2AClientTimeoutError:
                print(
                    "Request timed out waiting for the server response. "
                    f"Increase LOAN_CLOSURE_CLIENT_TIMEOUT_SECONDS (current: {timeout_seconds})."
                )
            except Exception as error:
                print(f"Request failed: {error}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a loan closure A2A request.")
    parser.add_argument(
        "--server-url",
        default=None,
        help="A2A server URL; defaults to LOAN_CLOSURE_AGENT_URL or localhost:8090",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run_prompt_loop(args.server_url))
    except KeyboardInterrupt:
        print("\nExited.")


if __name__ == "__main__":
    main()
