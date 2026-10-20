# Vertex AI Search Policy Agent

This is an isolated A2A loan-policy agent that uses the built-in ADK `VertexAiSearchTool`.

It does not use a vector database, custom embeddings, Vector Search indexes, index endpoints, or datapoint upload scripts.

## Setup

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag_vertex_ai_new
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Authenticate with Application Default Credentials and set the quota project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT"
```

Update `.env` with the Vertex AI Search datastore resource that contains the policy documents.

## Run

```bash
unset GOOGLE_API_KEY
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
.venv/bin/python policy_server.py
```

In another terminal:

```bash
.venv/bin/python policy_client.py --server-url http://localhost:8090
```

Health check:

```bash
curl http://localhost:8090/healthz
```
