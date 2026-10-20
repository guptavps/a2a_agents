# Intent Workflow and Loan-Closure Agent Runbook

This runbook covers installing dependencies, checking the Python sources, and running the loan-closure A2A agent behind the intent workflow. Commands assume the current directory is the workspace's `a2a/` directory:

```sh
cd /Users/vikasg/Documents/python_work/agent_1/a2a
```

The examples use the dedicated `intent_detection/.venv`, the loan-closure agent on port `8094`, and the workflow server on port `8092`. The explicit loan-agent port avoids colliding with other local services.

## One-Time Setup

Create the environment if it does not already exist, then install the declared dependencies:

```sh
python3.13 -m venv intent_detection/.venv
./intent_detection/.venv/bin/python -m pip install --upgrade pip
./intent_detection/.venv/bin/python -m pip install -r intent_detection/requirements.txt
```

Configure Vertex AI in each server terminal from the active gcloud project. Do not leave the project as a placeholder such as `your-project-id`:

```sh
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ "$GOOGLE_CLOUD_PROJECT" = "(unset)" ]; then
  echo "Set a Google Cloud project with: gcloud config set project PROJECT_ID"
  return 1
fi
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_LOCATION=global
unset GOOGLE_API_KEY
```

Confirm the Vertex AI API is enabled for that project:

```sh
gcloud services list --enabled --project="$GOOGLE_CLOUD_PROJECT" \
  --filter='config.name:aiplatform.googleapis.com' \
  --format='value(config.name)'
```

If that prints nothing and you have permission to enable services, enable the API:

```sh
gcloud services enable aiplatform.googleapis.com --project="$GOOGLE_CLOUD_PROJECT"
```

Authenticate once if Application Default Credentials are not already configured:

```sh
gcloud auth application-default login
```

## Build and Test

This Python project has no separate binary build step. Installing requirements and compiling the modules checks the runnable sources; the unit suite is offline and does not invoke the model.

```sh
./intent_detection/.venv/bin/python -m compileall -q intent_detection
PYTHONPATH=. ./intent_detection/.venv/bin/python -m unittest discover -s intent_detection -p 'test_*.py' -v
```

## Run the Services

Open three terminals, all with the working directory set to `a2a`. Export the Vertex AI variables from the One-Time Setup section in both server terminals.

Terminal 1, start the loan-closure A2A agent:

```sh
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project 2>/dev/null)"
export GOOGLE_CLOUD_LOCATION=global
unset GOOGLE_API_KEY
PYTHONPATH=. LOAN_CLOSURE_AGENT_PORT=8094 \
  ./intent_detection/.venv/bin/python -m intent_detection.loan_closure_agent
```

Terminal 2, start the intent workflow and point it at the loan agent:

```sh
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project 2>/dev/null)"
export GOOGLE_CLOUD_LOCATION=global
unset GOOGLE_API_KEY
export LOAN_CLOSURE_AGENT_URL=http://localhost:8094
PYTHONPATH=. ./intent_detection/.venv/bin/python -m intent_detection.workflow_server
```

Terminal 3, start the interactive workflow client:

```sh
PYTHONPATH=. ./intent_detection/.venv/bin/python \
  -m intent_detection.intent_detector_client \
  --server-url http://localhost:8092 \
  --context-id loan-closure-local-test
```

Try a prompt such as `Please close loan TEST-001`. Reuse `loan-closure-local-test` to continue the same conversation. Enter `exit` to stop the client; use Ctrl+C in either server terminal to stop that server.

## Check the Agent Card

With Terminal 1 running, check that the nested loan agent's A2A card is available:

```sh
curl --fail http://localhost:8094/.well-known/agent-card.json
```

With Terminal 2 running, the workflow agent card is available at:

```sh
curl --fail http://localhost:8092/.well-known/agent-card.json
```

## Session Notes

The workflow client reuses its A2A `context_id`. The workflow server maps that value to its ADK session, and the remote-agent integration forwards the workflow session ID as the loan agent's A2A `context_id`. The context builder separately forwards recent user turns and the validated intent decision.

By default, both services use in-memory session services. Session state is available only while the corresponding server process remains alive and is not shared between the two services. For persistence across restarts or replicas, configure the existing Vertex AI session service for each service with its own valid `GOOGLE_CLOUD_AGENT_ENGINE_ID`, project, and location settings.

## Updating This Runbook

When changing a service port, environment variable, module entry point, dependency, or session configuration, update the matching commands and notes here. Re-run the Build and Test commands after code changes, and verify both card endpoints after changing A2A server startup or configuration.
