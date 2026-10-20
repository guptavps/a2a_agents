import argparse
import asyncio
import os
from uuid import uuid4

import httpx
from a2a.client import create_client
from a2a.client.client import ClientConfig
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import TransportProtocol
from dotenv import load_dotenv

load_dotenv()


async def main_async(server_url: str) -> None:
    client = await create_client(
        server_url,
        client_config=ClientConfig(
            supported_protocol_bindings=[TransportProtocol.HTTP_JSON],
            httpx_client=httpx.AsyncClient(timeout=120),
        ),
    )
    try:
        prompt = input("Policy question: ").strip()
        if not prompt:
            return
        request = SendMessageRequest(
            message=Message(
                message_id=str(uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text=prompt)],
            )
        )
        async for response in client.send_message(request):
            if response.HasField("task"):
                for artifact in response.task.artifacts:
                    for part in artifact.parts:
                        if part.text:
                            print(part.text)
            elif response.HasField("message"):
                for part in response.message.parts:
                    if part.text:
                        print(part.text)
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server-url",
        default=os.getenv("A2A_RAG_URL", "http://localhost:8090"),
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.server_url))


if __name__ == "__main__":
    main()
