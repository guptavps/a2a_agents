# Local Loan Closure A2A Agent

This folder contains a minimal local ADK agent, a FastMCP loan-closure tool, and an interactive A2A client. It does not include Agents CLI scaffolding or deploy cloud resources.

## Install

Use Python 3.13 and create the virtual environment in this folder:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set Vertex AI environment variables before starting the agent, or copy `.env.example` to `.env` and fill in the project ID:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=global
```

Authenticate with Application Default Credentials using `gcloud auth application-default login`.

## Run

Terminal 1:

```bash
.venv/bin/python loan_closure_agent.py
```

Terminal 2:

```bash
.venv/bin/python loan_closure_client.py
```

Enter prompts repeatedly, for example `Please close loan TEST-001`. Type `exit` or `quit` to stop the client. Override the agent URL with `--server-url`.
