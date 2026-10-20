import logging
import os
import warnings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
)

# Must run before ADK imports so its experimental-feature warnings are hidden from the logs.
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]", category=UserWarning)

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.apps import App
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from starlette.middleware.cors import CORSMiddleware

from intent_detection.intent_detector_agent_card import build_agent_card
from intent_detection.intent_routing_workflow import intent_routing_workflow

load_dotenv()

APP_NAME = "workflow_app"
PORT = int(os.getenv("INTENT_DETECTOR_AGENT_PORT", "8092"))

app = App(name=APP_NAME, root_agent=intent_routing_workflow)


def _create_session_service():
    agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    if not agent_engine_id:
        return InMemorySessionService()

    from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService

    return VertexAiSessionService(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-central1"),
        agent_engine_id=agent_engine_id,
    )


agent_card = build_agent_card(
    name="intent_detector_agent",
    description=intent_routing_workflow.description,
    port=PORT,
)

runner = Runner(
    app=app,
    session_service=_create_session_service(),
    artifact_service=InMemoryArtifactService(),
)

a2a_app = to_a2a(
    intent_routing_workflow,
    host="0.0.0.0",
    port=PORT,
    runner=runner,
    protocol="http",
    agent_card=agent_card,
)

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

# No credentials are used, so allowing any request header is safe; origins stay an explicit allowlist.
a2a_app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def main() -> None:
    import uvicorn

    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
