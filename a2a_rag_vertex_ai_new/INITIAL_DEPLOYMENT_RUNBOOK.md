# Initial GKE Deployment Runbook

This runbook deploys the A2A loan-policy RAG service from this directory to the existing GKE cluster. It uses the Vertex AI Python SDK at runtime through Workload Identity, an internal Kubernetes Service, and a temporary HTTP-only GKE Ingress for testing.

> HTTP Ingress is public and unencrypted. Use it only for testing. Do not send sensitive data. Before production, use HTTPS and add authentication such as IAP or an authenticated gateway.

## Resource values

```bash
export PROJECT_ID="genai-ai-agents-project"
export REGION="us-central1"
export CLUSTER="loan-closure-cluster"
export REPOSITORY="loan-closure"
export IMAGE_NAME="a2a-rag"
export IMAGE_TAG="0.1.0"
export IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
export NAMESPACE="default"
export GSA_NAME="loan-policy-agent"
export GSA_EMAIL="${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export KSA_NAME="loan-policy-agent"
```

## 1. Select the existing cluster

This updates the local kubeconfig context; it does not change the cluster.

```bash
gcloud container clusters get-credentials "$CLUSTER" \
  --project="$PROJECT_ID" \
  --region="$REGION"

kubectl config current-context
kubectl get nodes -o wide
```

Confirm the context is for `loan-closure-cluster` and nodes are `Ready` before continuing.

## 2. Build and push the application image

Docker is not required locally. Cloud Build builds from the Dockerfile and pushes to the existing Artifact Registry repository.

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag_vertex_ai_new

gcloud builds submit \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --tag="$IMAGE_URI" \
  .
```

Check the build result before proceeding. Use a new unique image tag for later builds; do not overwrite a tag that a running deployment may be using.

## 3. Create the runtime Google service account and grant access

The agent needs permission to call Vertex AI and read the policy PDF manifest from GCS. These commands are safe to repeat for an existing service account and IAM member.

```bash
if ! gcloud iam service-accounts describe "$GSA_EMAIL" \
  --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$GSA_NAME" \
    --project="$PROJECT_ID" \
    --display-name="Loan Policy A2A Agent"
fi

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${GSA_EMAIL}" \
  --role="roles/aiplatform.user"

gcloud storage buckets add-iam-policy-binding \
  gs://loan-policy-bucket-001 \
  --member="serviceAccount:${GSA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

## 4. Connect the Kubernetes service account with Workload Identity

The cluster Workload Identity pool is `genai-ai-agents-project.svc.id.goog`.

```bash
kubectl create serviceaccount "$KSA_NAME" \
  --namespace="$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -

gcloud iam service-accounts add-iam-policy-binding "$GSA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"

kubectl annotate serviceaccount "$KSA_NAME" \
  --namespace="$NAMESPACE" \
  "iam.gke.io/gcp-service-account=${GSA_EMAIL}" \
  --overwrite

kubectl get serviceaccount "$KSA_NAME" -n "$NAMESPACE" -o yaml
```

The service account should have the `iam.gke.io/gcp-service-account` annotation. No service-account key file should be created or mounted.

## 5. Apply the Deployment and internal Service

The Deployment uses the dedicated Kubernetes service account, container port `8080`, Vertex AI environment variables, and `/healthz` probes.

```bash
kubectl apply -f k8s/rag-agent.yaml
kubectl rollout status deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" \
  --timeout=5m

kubectl get deployment,pods,service -n "$NAMESPACE" \
  -l app=loan-policy-rag-agent -o wide
kubectl logs deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" --tail=100
```

Do not continue unless the pod is Ready and logs show the server started successfully.

## 6. Create the temporary HTTP Ingress

The Ingress uses the GKE `gce` Ingress controller. Its `BackendConfig` probes `/healthz`; the BackendConfig annotation is on the Service in `k8s/rag-agent.yaml`.

```bash
kubectl apply -f k8s/rag-agent.yaml -f k8s/http-ingress.yaml
kubectl get ingress loan-policy-rag-http -n "$NAMESPACE" -w
```

Wait until the `ADDRESS` field contains an external IP, then stop watching with `Ctrl+C` and set it:

```bash
export INGRESS_IP="REPLACE_WITH_INGRESS_ADDRESS"
```

## 7. Advertise the Ingress URL in the Agent Card

A2A clients discover the endpoint URL from the Agent Card. Set it to the Ingress URL rather than `localhost`:

```bash
kubectl set env deployment/loan-policy-rag-agent \
  A2A_RAG_URL="http://${INGRESS_IP}" \
  -n "$NAMESPACE"

kubectl rollout status deployment/loan-policy-rag-agent \
  -n "$NAMESPACE" \
  --timeout=5m
```

If you later apply a Deployment manifest that does not include `A2A_RAG_URL`, that apply may remove this runtime override. Preserve the value in your deployment configuration or set it again after applying.

## 8. Verify health, Agent Card, and A2A response

```bash
curl --fail "http://${INGRESS_IP}/healthz"
curl --fail --silent "http://${INGRESS_IP}/.well-known/agent-card.json"
```

The Agent Card interface URL should be `http://${INGRESS_IP}`. Then send an A2A question from the local project environment:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag_vertex_ai_new
.venv/bin/python policy_client.py --server-url "http://${INGRESS_IP}"
```

Enter a policy question. Confirm the answer cites the source page.

## 9. Remove the temporary public HTTP Ingress when finished testing

```bash
kubectl delete ingress loan-policy-rag-http -n "$NAMESPACE"
```

The Deployment and internal ClusterIP Service remain. For continued remote access, configure a proper HTTPS hostname and authentication before recreating public access.
