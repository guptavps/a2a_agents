# Loan Closure Agent Runtime Runbook

This project uses the manually maintained `agents-cli-manifest.yaml`; do not run `agents-cli scaffold` or `agents-cli scaffold enhance` here. Deployment target is Agent Runtime in `us-central1`.

Previous test deployment (deleted 2026-10-06): `projects/315667794922/locations/us-central1/reasoningEngines/8759500725479800832` (`loan-closure-agent`). It used 1 CPU, 1Gi memory, minimum 0 instances, maximum 1 instance, and concurrency 1. A remote A2A smoke test with synthetic loan ID `TEST-DEPLOY-001` succeeded. No Agent Runtime deployment is currently present.

## Prerequisites

- Google Cloud billing is active on `genai-ai-agents-project`.
- `gcloud` is authenticated with Application Default Credentials and the active project is correct.
- Agents CLI is installed (`uv tool install google-agents-cli`).
- Python source and `requirements.txt` compile/install locally.
- The container packages `loan_closure_agent.py`, `loan_closure_agent_card.py`, and `mcp_server.py` together. The MCP server is started as a local stdio subprocess inside the agent container.

Verify identity, project, and billing before deployment:

```bash
gcloud auth list
gcloud config get-value project
gcloud billing projects describe genai-ai-agents-project \
  --format='yaml(projectId,billingAccountName,billingEnabled)'
```

Set the target project explicitly:

```bash
gcloud config set project genai-ai-agents-project
```

## Initial Deployment

Run from this folder. Preview first; dry-run does not create resources:

```bash
agents-cli info
agents-cli deploy \
  --project genai-ai-agents-project \
  --region us-central1 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 1 \
  --update-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=global \
  --dry-run
```

After confirming the preview targets `loan-closure-agent` in `us-central1`, deploy with the same sizing flags, omitting `--dry-run`:

```bash
agents-cli deploy \
  --project genai-ai-agents-project \
  --region us-central1 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 1 \
  --update-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=global
```

Agents CLI's real deployment path currently requires an integer CPU value; `--cpu 0.5` passes dry-run but fails during deployment parsing. Agent Runtime also requires memory in GiB units; `512Mi` is rejected, so the minimum accepted test setting is `1Gi`. Do not raise `min-instances` unless a warm instance is intentionally needed. `min-instances 0` allows scale-to-zero, but model requests and other services may still incur charges.

## Subsequent Builds And Updates

1. Edit the agent, MCP server, or dependencies in this project.
2. Compile and test locally:

```bash
.venv/bin/python -m py_compile \
  loan_closure_agent.py loan_closure_agent_card.py mcp_server.py loan_closure_client.py
```

3. Preview the update with the same `agents-cli deploy ... --dry-run` command above.
4. Deploy the update with the same command and sizing flags. The CLI uses the manifest/project name to identify the Agent Runtime deployment. To avoid accidentally creating a second resource, use `--update-only` for updates after the initial deployment:

```bash
agents-cli deploy \
  --project genai-ai-agents-project \
  --region us-central1 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 1 \
  --update-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=global \
  --update-only
```

5. Record the Agent Runtime resource name/ID returned by the deployment command.

## Verify

The A2A card is served through the Agent Runtime API endpoint. Use the resource ID from deployment output:

```bash
export AGENT_ENGINE_ID='REPLACE_WITH_DEPLOYED_RESOURCE_ID'
curl --fail --silent \
  "https://us-central1-aiplatform.googleapis.com/reasoningEngines/v1/projects/genai-ai-agents-project/locations/us-central1/reasoningEngines/${AGENT_ENGINE_ID}/api/.well-known/agent-card.json"
```

Send an A2A test request with Agents CLI using a synthetic loan ID. Do not use a real customer's loan ID for smoke tests.

```bash
agents-cli run \
  --url "https://us-central1-aiplatform.googleapis.com/reasoningEngines/v1/projects/genai-ai-agents-project/locations/us-central1/reasoningEngines/${AGENT_ENGINE_ID}/api/" \
  --mode a2a \
  --app-name loan_closure_agent \
  "Please close synthetic test loan TEST-001; this is a deployment smoke test."
```

Confirm the agent reports success and inspect the Agent Runtime logs for the MCP `close_loan` call.

## Remove The Test Deployment

First list deployments and confirm the exact resource ID:

```bash
agents-cli deploy --list --project genai-ai-agents-project --region us-central1
```

The installed Agents CLI and gcloud versions do not expose a delete command for Agent Runtime resources. Open the Google Cloud Console's Agent Runtime resources for `genai-ai-agents-project` in `us-central1`, verify the display name and resource ID match `loan-closure-agent` and the ID above, then delete that resource. Do not delete unrelated Agent Runtime resources.

After deletion, rerun `agents-cli deploy --list --project genai-ai-agents-project --region us-central1` and confirm the loan-closure resource is absent. Deleting the Agent Runtime resource stops its runtime charges. Gemini model inference, logging, and other separately provisioned services may have separate charges.
