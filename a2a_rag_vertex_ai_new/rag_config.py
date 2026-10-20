import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class RagSettings:
    project_id: str
    data_store_id: str
    location: str = "global"
    max_results: int = 5


def load_settings() -> RagSettings:
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    data_store_id = os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID", "").strip()
    location = os.getenv("VERTEX_AI_SEARCH_LOCATION", "global").strip()
    max_results_text = os.getenv("LOAN_POLICY_SEARCH_MAX_RESULTS", "5").strip()

    missing = []
    if not project_id:
        missing.append("GOOGLE_CLOUD_PROJECT")
    if not data_store_id:
        missing.append("VERTEX_AI_SEARCH_DATA_STORE_ID")
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")

    try:
        max_results = int(max_results_text)
    except ValueError as exc:
        raise ValueError("LOAN_POLICY_SEARCH_MAX_RESULTS must be an integer") from exc
    if max_results < 1:
        raise ValueError("LOAN_POLICY_SEARCH_MAX_RESULTS must be greater than zero")

    return RagSettings(
        project_id=project_id,
        data_store_id=data_store_id,
        location=location,
        max_results=max_results,
    )
