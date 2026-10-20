import os

from loan_closure_agent_card import LoanClosureAgentCard
from loan_closure_executor import LoanClosureExecutor
from a2a.server.tasks import InMemoryPushNotificationConfigStore, InMemoryTaskStore, PushNotificationConfigStore, TaskStore, BasePushNotificationSender
import httpx
from a2a.server.request_handlers import DefaultRequestHandler
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.routes.rest_routes import create_rest_routes
import uvicorn

async def healthz(request):
    return PlainTextResponse("ok")

def main() -> None:
    agent_card = LoanClosureAgentCard().get_agent_card()
    executor = LoanClosureExecutor()
    task_store = InMemoryTaskStore()
    push_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(httpx_client=httpx.AsyncClient(), config_store=push_store)
    request_handler = DefaultRequestHandler(
                                agent_card=agent_card,
                                agent_executor=executor, 
                                task_store=task_store, 
                                push_config_store=push_store,
                                push_sender=push_sender)
    app = Starlette()
    app.add_route("/healthz", healthz, methods=["GET"])
    app.router.routes.extend(create_agent_card_routes(agent_card))
    app.router.routes.extend(create_jsonrpc_routes(request_handler, rpc_url="/"))
    app.router.routes.extend(create_rest_routes(request_handler))

    port = int(os.getenv("LOAN_CLOSURE_AGENT_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
