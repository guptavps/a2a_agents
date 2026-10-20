import argparse
import io
import json
from pathlib import Path
from urllib.parse import urlparse

from google import genai
from google.cloud import aiplatform, storage
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (
    MatchingEngineIndexEndpoint,
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from pipeline_config import load_pipeline_config


_tracer = trace.get_tracer(__name__)


def _parse_gs_uri(bucket_uri: str) -> str:
    parsed = urlparse(bucket_uri)
    if parsed.scheme != "gs" or not parsed.netloc or parsed.path.strip("/"):
        raise ValueError("gcs.bucket_uri must be a bucket-only URI such as gs://bucket-name")
    return parsed.netloc


def _embed_question(config, question: str) -> list[float]:
    client = genai.Client(
        vertexai=True,
        project=config.project_id,
        location=config.region,
    )
    response = client.models.embed_content(
        model=config.rag.embedding_model,
        contents=[question],
        config={"output_dimensionality": config.vector_search.index_dimensions},
    )
    if not response.embeddings:
        raise RuntimeError("The embedding service returned no embedding")
    embedding = list(response.embeddings[0].values)
    if len(embedding) != config.vector_search.index_dimensions:
        raise ValueError(
            f"Question embedding has {len(embedding)} dimensions; "
            f"expected {config.vector_search.index_dimensions}"
        )
    return embedding


def _neighbor_id(neighbor) -> str:
    datapoint = getattr(neighbor, "datapoint", None)
    datapoint_id = getattr(datapoint, "datapoint_id", None)
    if datapoint_id:
        return datapoint_id
    neighbor_id = getattr(neighbor, "id", None)
    if neighbor_id:
        return neighbor_id
    raise RuntimeError(f"Could not read datapoint ID from Vector Search result: {neighbor!r}")


def _load_manifest(config) -> dict[str, dict]:
    bucket_name = _parse_gs_uri(config.gcs.bucket_uri)
    client = storage.Client(project=config.project_id)
    with _tracer.start_as_current_span("rag.gcs_manifest.load") as span:
        span.set_attribute("storage.system", "gcs")
        span.set_attribute("storage.object", config.gcs.manifest_object_name)
        try:
            manifest_bytes = client.bucket(bucket_name).blob(
                config.gcs.manifest_object_name
            ).download_as_bytes()
            records = {}
            for line in io.BytesIO(manifest_bytes).read().decode("utf-8").splitlines():
                record = json.loads(line)
                records[record["chunk_id"]] = record
        except Exception as exc:
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise
        span.set_attribute("storage.manifest.record_count", len(records))
        span.set_status(Status(StatusCode.OK))
    return records


def query_vector_search(
    question: str,
    config_path: str | Path = "pipeline_config.yaml",
) -> list[dict]:
    """Retrieve policy chunks from Vector Search and resolve their text from GCS."""
    config = load_pipeline_config(config_path)
    embedding = _embed_question(config, question)
    aiplatform.init(project=config.project_id, location=config.region)

    endpoints = aiplatform.MatchingEngineIndexEndpoint.list()
    matches = [
        endpoint
        for endpoint in endpoints
        if endpoint.display_name == config.vector_search.endpoint_display_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one endpoint named {config.vector_search.endpoint_display_name!r}; "
            f"found {len(matches)}"
        )

    # Reconstruct the resource so the SDK initializes its public match client.
    endpoint = MatchingEngineIndexEndpoint(
        index_endpoint_name=matches[0].resource_name,
        project=config.project_id,
        location=config.region,
    )
    with _tracer.start_as_current_span("rag.vector_search.find_neighbors") as span:
        span.set_attribute("db.system", "vertex_ai_vector_search")
        span.set_attribute(
            "vector_search.endpoint_name",
            config.vector_search.endpoint_display_name,
        )
        span.set_attribute(
            "vector_search.deployed_index_id",
            config.vector_search.deployed_index_id,
        )
        span.set_attribute(
            "vector_search.top_k",
            config.vector_search.retrieval_neighbors,
        )
        try:
            neighbors = endpoint.find_neighbors(
                deployed_index_id=config.vector_search.deployed_index_id,
                queries=[embedding],
                num_neighbors=config.vector_search.retrieval_neighbors,
            )[0]
        except Exception as exc:
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise
        span.set_status(Status(StatusCode.OK))
    manifest = _load_manifest(config)

    results = []
    for neighbor in neighbors:
        chunk_id = _neighbor_id(neighbor)
        record = manifest.get(chunk_id)
        if record is None:
            raise RuntimeError(
                f"No manifest record found for datapoint: {chunk_id}. "
                "The Vector Search index and manifest are out of sync; "
                "rebuild the index before querying."
            )
        results.append(
            {
                "chunk_id": chunk_id,
                "distance": getattr(neighbor, "distance", None),
                "source_uri": record["source_uri"],
                "page_number": record["page_number"],
                "text": record["text"],
            }
        )
    return results


def _synthesize_answer(config, question: str, results: list[dict]) -> str:
    context = "\n\n".join(
        f"[Source page {result['page_number']}]\n{result['text']}"
        for result in results
    )
    client = genai.Client(
        vertexai=True,
        project=config.project_id,
        location=config.region,
    )
    response = client.models.generate_content(
        model=config.gemini.model,
        contents=(
            "Answer the user's question using only the policy context below. "
            "If the context does not contain the answer, say that clearly. "
            "Do not invent requirements, fees, deadlines, or exceptions. "
            "Cite the source page for each material statement.\n\n"
            f"User question: {question}\n\nPolicy context:\n{context}"
        ),
        config={
            "temperature": config.gemini.temperature,
            "max_output_tokens": config.gemini.max_output_tokens,
        },
    )
    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned an empty answer")
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively query Vector Search and print matched policy chunks."
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Optional single question. Omit it to enter repeatable interactive mode.",
    )
    parser.add_argument("--config", type=Path, default=Path("pipeline_config.yaml"))
    args = parser.parse_args()

    questions = [args.question] if args.question else iter(input, "")
    if args.question is None:
        print("Enter a policy question, or type 'quit' to stop.")

    for question in questions:
        question = question.strip()
        if not question:
            if args.question is None:
                continue
            break
        if question.lower() in {"quit", "exit"}:
            break
        results = query_vector_search(question, args.config)
        config = load_pipeline_config(args.config)
        print(f"Retrieved {len(results)} policy chunks")
        print("\nAnswer:\n")
        print(_synthesize_answer(config, question, results))
        print("\nSources:")
        for result in results:
            print(f"- page {result['page_number']} ({result['chunk_id']})")


if __name__ == "__main__":
    main()
