# Intent Workflow With Loan Closure A2A

The intent workflow delegates `loan_closure` decisions to the A2A service in `intent_detection/loan_closure_agent/`. From the `a2a` directory, install dependencies into the intent-detection environment and run both services in separate terminals:

```sh
./intent_detection/.venv/bin/python -m pip install -r intent_detection/requirements.txt
```

Start the loan-closure A2A agent independently:

```sh
PYTHONPATH=. \
GOOGLE_GENAI_USE_VERTEXAI=TRUE \
GOOGLE_CLOUD_PROJECT=your-project-id \
GOOGLE_CLOUD_LOCATION=global \
./intent_detection/.venv/bin/python -m intent_detection.loan_closure_agent
```

Start the intent workflow:

```sh
PYTHONPATH=. \
GOOGLE_GENAI_USE_VERTEXAI=TRUE \
GOOGLE_CLOUD_PROJECT=your-project-id \
GOOGLE_CLOUD_LOCATION=global \
LOAN_CLOSURE_AGENT_URL=http://localhost:8090 \
./intent_detection/.venv/bin/python -m intent_detection.workflow_server
```

The loan agent listens on port `8090`; the workflow listens on port `8092`. Set `LOAN_CLOSURE_AGENT_URL` to the loan agent's base URL when it is hosted elsewhere. Set `LOAN_CLOSURE_AGENT_CARD_URL` to the full agent-card URL if the card is not at `/.well-known/agent-card.json` under that base URL.

Send prompts through the workflow client, keeping the same context ID to continue a conversation:

```sh
PYTHONPATH=. ./intent_detection/.venv/bin/python \
  -m intent_detection.intent_detector_client \
  --server-url http://localhost:8092 \
  --context-id loan-closure-conversation-1
```

The workflow forwards its ADK session ID as the downstream A2A `context_id`. The loan agent therefore keeps a corresponding session across delegated turns. Each request also includes recent user turns since the previous loan-agent handoff and the validated intent decision; internal classifier events and unrelated workflow state are not forwarded.

Both servers use in-memory session services by default, which preserve context only while each process remains alive. For sessions that must survive replicas or restarts, configure the existing Vertex AI session service on each service with that service's `GOOGLE_CLOUD_AGENT_ENGINE_ID`, plus project and location settings. Keep the workflow client context ID stable when continuing the conversation.
