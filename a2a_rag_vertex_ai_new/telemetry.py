import os

from google.adk.telemetry.google_cloud import get_gcp_exporters
from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry.sdk.resources import Resource


_configured = False


def configure_cloud_tracing(project_id: str) -> None:
    """Configure ADK OpenTelemetry trace export to Google Cloud Trace once."""
    global _configured
    if _configured:
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "loan-policy-rag-agent")
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "loan-policy",
            "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
            "deployment.environment.name": os.getenv("DEPLOYMENT_ENVIRONMENT", "development"),
            "gcp.project_id": project_id,
        }
    )
    gcp_exporters = get_gcp_exporters(enable_cloud_tracing=True)
    maybe_set_otel_providers([gcp_exporters], otel_resource=resource)
    _configured = True