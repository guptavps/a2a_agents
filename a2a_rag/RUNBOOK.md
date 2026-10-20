# Loan Policy RAG Runbook

This runbook creates a stream-update Vertex AI Vector Search index, deploys it to a public index endpoint, uploads vector datapoints, verifies retrieval, and runs the local A2A service.

Do not place API keys, access tokens, or service-account JSON files in this document.

## Prerequisites

Run these commands from `a2a/a2a_rag`:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag

# Activate the project environment.
. .venv/bin/activate

export PROJECT_ID="genai-ai-agents-project"
export REGION="us-central1"
export DIMENSIONS="768"
export INDEX_DISPLAY_NAME="loan-policy-stream-index"
export ENDPOINT_DISPLAY_NAME="loan-policy-stream-endpoint"
export DEPLOYED_INDEX_ID="loan_policy_stream_deployed"

gcloud config set project "$PROJECT_ID"
gcloud auth application-default set-quota-project "$PROJECT_ID"
```

## Enable APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  containerregistry.googleapis.com \
  run.googleapis.com \
  --project="$PROJECT_ID"
```

## Create the index

The index must use `stream-update` because datapoints are uploaded with `upsertDatapoints`.

```bash
mkdir -p tmp

cat > tmp/vector_index_metadata.json <<'JSON'
{
  "config": {
    "dimensions": 768,
    "approximateNeighborsCount": 10,
    "distanceMeasureType": "COSINE_DISTANCE",
    "shardSize": "SHARD_SIZE_SMALL",
    "algorithmConfig": {
      "treeAhConfig": {
        "leafNodeEmbeddingCount": 500
      }
    }
  }
}
JSON

gcloud ai indexes create \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display-name="$INDEX_DISPLAY_NAME" \
  --metadata-file=tmp/vector_index_metadata.json \
  --index-update-method=stream-update

export INDEX_ID="$(
  gcloud ai indexes list \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --filter="displayName=$INDEX_DISPLAY_NAME" \
    --format="value(name.basename())"
)"

echo "INDEX_ID=$INDEX_ID"
```

## Create the index endpoint

```bash
gcloud ai index-endpoints create \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display-name="$ENDPOINT_DISPLAY_NAME" \
  --public-endpoint-enabled

export INDEX_ENDPOINT_ID="$(
  gcloud ai index-endpoints list \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --filter="displayName=$ENDPOINT_DISPLAY_NAME" \
    --format="value(name.basename())"
)"

echo "INDEX_ENDPOINT_ID=$INDEX_ENDPOINT_ID"
```

## Deploy the index

```bash
gcloud ai index-endpoints deploy-index "$INDEX_ENDPOINT_ID" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --index="$INDEX_ID" \
  --deployed-index-id="$DEPLOYED_INDEX_ID" \
  --display-name="$DEPLOYED_INDEX_ID" \
  --min-replica-count=1 \
  --max-replica-count=1
```

Wait for deployment to finish. The endpoint must contain `deployedIndexes` before querying it.

```bash
gcloud ai index-endpoints describe "$INDEX_ENDPOINT_ID" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="yaml(name,publicEndpointDomain,deployedIndexes)"

export ENDPOINT_DOMAIN="$(
  gcloud ai index-endpoints describe "$INDEX_ENDPOINT_ID" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format="value(publicEndpointDomain)"
)"

echo "ENDPOINT_DOMAIN=$ENDPOINT_DOMAIN"
```

## Generate vector records

The application pipeline parses, chunks, embeds, and writes the records used below.

```bash
.venv/bin/python ingest_documents.py \
  policy-docs \
  tmp/vector_records.jsonl
```

Expected output resembles:

```text
Wrote 1 vector records to tmp/vector_records.jsonl
```

## Upload datapoints

Convert the generated JSONL records to the Vector Search REST payload:

```bash
python3 - <<'PY'
import json
from pathlib import Path

records = [
    json.loads(line)
    for line in Path("tmp/vector_records.jsonl").read_text().splitlines()
]

payload = {
    "datapoints": [
        {
            "datapointId": record["id"],
            "featureVector": record["embedding"],
            "restricts": [
                {
                    "namespace": item["namespace"],
                    "allowList": item.get("allow", item.get("allowList", [])),
                }
                for item in record.get("restricts", [])
            ],
        }
        for record in records
    ]
}

Path("tmp/upsert_datapoints.json").write_text(
    json.dumps(payload),
    encoding="utf-8",
)
print(f"Prepared {len(records)} datapoints")
PY
```

Upload the datapoints to the index:

```bash
export ACCESS_TOKEN="$(gcloud auth print-access-token)"

curl --fail-with-body -sS -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/indexes/${INDEX_ID}:upsertDatapoints" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary @tmp/upsert_datapoints.json
```

Expected response:

```json
{}
```

## Query the deployed index

Create a nearest-neighbor request using one generated embedding:

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(
    Path("tmp/vector_records.jsonl").read_text().splitlines()[0]
)

payload = {
    "deployedIndexId": "loan_policy_stream_deployed",
    "queries": [
        {
            "datapoint": {
                "featureVector": record["embedding"]
            },
            "neighborCount": 5
        }
    ]
}

Path("tmp/find_neighbors.json").write_text(
    json.dumps(payload),
    encoding="utf-8",
)
PY

curl --fail-with-body -sS -X POST \
  "https://${ENDPOINT_DOMAIN}/v1/projects/${PROJECT_ID}/locations/${REGION}/indexEndpoints/${INDEX_ENDPOINT_ID}:findNeighbors" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary @tmp/find_neighbors.json
```

A successful response has HTTP `200` and contains a neighbor such as `loan-closure-policy-0000`.

## Configure the application

Set the following values in `rag_config.yaml` or environment variables:

```yaml
project_id: genai-ai-agents-project
location: us-central1
index_id: "YOUR_INDEX_ID"
index_endpoint_id: "YOUR_INDEX_ENDPOINT_ID"
index_endpoint_domain: "YOUR_PUBLIC_ENDPOINT_DOMAIN"
```

For the currently deployed resources:

```yaml
index_id: "5750276488477802496"
index_endpoint_id: "6416580534910058496"
index_endpoint_domain: "596876783.us-central1-315667794922.vdb.vertexai.goog"
```

Use Vertex AI mode and ADC credentials. Do not configure `GOOGLE_API_KEY` for this flow.

## Run the local A2A service

```bash
unset GOOGLE_API_KEY
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="$REGION"
export A2A_RAG_PORT=8091

.venv/bin/python policy_server.py
```

In a second terminal:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/a2a_rag
. .venv/bin/activate

curl --fail http://localhost:8091/healthz
printf '%s\n' \
  'What must be verified before confirming a loan closure?' \
  | .venv/bin/python policy_client.py --server-url http://localhost:8091
```

## Resource inspection and cleanup

Inspect resources:

```bash
gcloud ai indexes list \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="table(name,displayName)"

gcloud ai index-endpoints list \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="table(name,displayName,publicEndpointDomain)"
```

Delete the deployment before deleting the endpoint or index:

```bash
gcloud ai index-endpoints undeploy-index "$INDEX_ENDPOINT_ID" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --deployed-index-id="$DEPLOYED_INDEX_ID"

gcloud ai index-endpoints delete "$INDEX_ENDPOINT_ID" \
  --project="$PROJECT_ID" \
  --region="$REGION"

gcloud ai indexes delete "$INDEX_ID" \
  --project="$PROJECT_ID" \
  --region="$REGION"
```
