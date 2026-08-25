"""Assurance SDK. Reference architecture Layer 1.

Deterministic. No LLM. Makes a service observable by construction rather than
by hope.

Emits REAL OpenTelemetry spans over OTLP. The declared topology in
spans.declared.yaml is a contract, not documentation: emitting an undeclared
span raises. Adding one means editing a reviewed file.

Every span carries work_item.id, git.sha and build.id -- that is the
traceability chain `factory trace` reads.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

import yaml
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pydantic import BaseModel, Field


class ServiceManifest(BaseModel):
    """Claims the service makes about itself.

    Deliberately *claims*, not facts: a container self-reporting its identity
    proves nothing under a threat model. The platform establishes the real image
    digest; these are cross-checked against it.
    """

    service: str
    build_id: str = Field(default_factory=lambda: os.getenv("BUILD_ID", "local"))
    git_sha: str = Field(default_factory=lambda: os.getenv("GIT_SHA", "unknown"))
    image_digest: str = Field(default_factory=lambda: os.getenv("IMAGE_DIGEST", "unknown"))
    work_item_id: str = Field(
        default_factory=lambda: os.getenv("WORK_ITEM_ID", "unknown"),
        description="On every span. This is the traceability chain.",
    )
    assurance_sdk_version: str = "0.2.0"


class UndeclaredSpan(Exception):
    """Code emitted a span absent from spans.declared.yaml.

    Fails closed on purpose. Allowing undeclared spans makes the declared
    topology decorative and the span_topology gate meaningless.
    """


class Assurance:
    def __init__(
        self,
        service: str,
        declared_path: str = "spans.declared.yaml",
        *,
        export: bool = True,
    ) -> None:
        self.manifest = ServiceManifest(service=service)
        declared = yaml.safe_load(Path(declared_path).read_text())
        self.declared_spans: frozenset[str] = frozenset(declared["spans"])
        self.declared_metrics: frozenset[str] = frozenset(declared["metrics"])
        self.observed_spans: set[str] = set()

        resource = Resource.create({
            "service.name": service,
            "service.version": self.manifest.build_id,
            "git.sha": self.manifest.git_sha,
            "build.id": self.manifest.build_id,
            "work_item.id": self.manifest.work_item_id,
        })
        provider = TracerProvider(resource=resource)
        if export:
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            exporter = (
                OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
                if endpoint
                else ConsoleSpanExporter()
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service)

    @contextlib.contextmanager
    def span(self, name: str, **attributes: str | float | bool) -> Iterator[None]:
        """Emit a real OTLP span. Refuses anything not declared."""
        if name not in self.declared_spans:
            raise UndeclaredSpan(
                f"'{name}' is not in spans.declared.yaml. "
                "Declare it (which requires a review) or do not emit it."
            )
        self.observed_spans.add(name)
        with self._tracer.start_as_current_span(name) as span:
            span.set_attribute("work_item.id", self.manifest.work_item_id)
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield

    def coverage(self) -> dict[str, object]:
        """What `factory trace` reads. Absence of evidence is not evidence of absence."""
        missing = sorted(self.declared_spans - self.observed_spans)
        return {
            "declared": len(self.declared_spans),
            "observed": len(self.observed_spans),
            "missing": missing,
            "complete": not missing,
            "manifest": self.manifest.model_dump(),
        }
