# Incremental GKE Deployment Runbook

Use this runbook to publish application or configuration changes after the initial deployment. It builds a new image tag, updates the existing Deployment, waits for rollout, and verifies the service. It does not recreate the GKE cluster, Workload Identity service accounts, Vector Search index, endpoint, or Ingress.

The currently tested access mode is a temporary public HTTP Ingress. Do not use it for sensitive traffic; use HTTPS and authentication before production.

## 1. Set deployment values

```bash
export PROJECT_ID="genai-ai-agents-project"
export REGION="us-central1"
export NAMESPACE="default"
export IMAGE_URI_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/loan-closure/a2a-rag"
export IMAGE_TAG="0.1.1"
export IMAGE_URI="${IMAGE_URI_BASE}:${IMAGE_TAG}"
```

For each update, choose a new immutable tag (`0.1.2`, `0.2.0`, or a commit SHA). Avoid reusing a tag with `imagePullPolicy: IfNotPresent`.

## 2. Build and push the new image

Run from the application directory:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag_vertex_ai_new

gcloud builds submit \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --tag="$IMAGE_URI" \
  .
```

Wait for Cloud Build to report success before updating GKE.

## 3. Update the existing Deployment image

```bash
kubectl set image deployment/loan-policy-rag-agent \
  agent="$IMAGE_URI" \
  -n "$NAMESPACE"

kubectl rollout status deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" \
  --timeout=5m
```

This preserves the existing Service, Ingress, Kubernetes service account, and runtime environment, including `A2A_RAG_URL`.

## 4. Inspect rollout and logs

```bash
kubectl get deployment,pods -n "$NAMESPACE" \
  -l app=loan-policy-rag-agent -o wide
kubectl logs deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" --tail=100
```

If rollout fails, inspect the pod events and previous container logs:

```bash
kubectl describe pods -n "$NAMESPACE" \
  -l app=loan-policy-rag-agent
kubectl logs deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" --previous --tail=150
```

## 5. Smoke-test through the existing HTTP Ingress

Set `INGRESS_IP` to the current address shown by:

```bash
kubectl get ingress loan-policy-rag-http -n "$NAMESPACE" -o wide
```

Then verify health and Agent Card:

```bash
export INGRESS_IP="REPLACE_WITH_INGRESS_ADDRESS"
curl --fail "http://${INGRESS_IP}/healthz"
curl --fail --silent "http://${INGRESS_IP}/.well-known/agent-card.json"
```

Test an A2A interaction:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag_vertex_ai_new
.venv/bin/python policy_client.py --server-url "http://${INGRESS_IP}"
```

Check the response, citations, and pod logs for errors.

## 6. Roll back the application image if needed

```bash
kubectl rollout undo deployment/loan-policy-rag-agent -n "$NAMESPACE"
kubectl rollout status deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" \
  --timeout=5m
```

## Configuration changes

The application reads `pipeline_config.yaml` from the image. If that file changes, build and deploy a new image tag using this runbook. If you change the Ingress address, update `A2A_RAG_URL` to the new URL and wait for the Deployment rollout before testing.
