import os

import httpx
import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.routes.rest_routes import create_rest_routes
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

from policy_agent_card import build_agent_card
from policy_executor import PolicyExecutor
from rag_config import load_settings


def healthz(request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def build_app() -> Starlette:
    settings = load_settings()
    agent_card = build_agent_card()
    push_store = InMemoryPushNotificationConfigStore()
    request_handler = DefaultRequestHandler(
        agent_executor=PolicyExecutor(settings),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
        push_config_store=push_store,
        push_sender=BasePushNotificationSender(
            httpx_client=httpx.AsyncClient(),
            config_store=push_store,
        ),
    )
    app = Starlette()
    app.add_route("/healthz", healthz, methods=["GET"])
    app.router.routes.extend(create_agent_card_routes(agent_card))
    app.router.routes.extend(create_jsonrpc_routes(request_handler, rpc_url="/"))
    app.router.routes.extend(create_rest_routes(request_handler))
    return app


def main() -> None:
    port = int(os.getenv("A2A_RAG_PORT", "8090"))
    uvicorn.run(build_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
