"""nokinc-demo-payments -- the factory's first target.

Endpoints arrive via the factory. This file exists so the repo builds, the
assurance wiring is present, and the gates have something to run against.
"""

from __future__ import annotations

from fastapi import FastAPI

from payments.assurance import Assurance

assurance = Assurance(service="nokinc-demo-payments")
app = FastAPI(title="nokinc-demo-payments")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"status": "ok", "manifest": assurance.manifest.model_dump()}


@app.get("/assurance/coverage")
def coverage() -> dict[str, object]:
    """Span coverage. Read by `factory trace`."""
    return assurance.coverage()


# Story 1 adds:  POST /refunds  ·  GET /refunds/{id}  ·  GET /orders/{id}
