"""FROZEN CONTRACT. The assurance wiring must not regress.

If these fail, the service has stopped being assurance-designed and no feature
work should merge until they pass again.
"""
import pytest

from payments.assurance import Assurance, UndeclaredSpan


def test_undeclared_span_is_refused() -> None:
    """Allowing undeclared spans makes the declared topology decorative."""
    a = Assurance("test", export=False)
    with pytest.raises(UndeclaredSpan), a.span("refund.sneaky_undeclared"):
        pass


def test_declared_span_is_recorded() -> None:
    a = Assurance("test", export=False)
    with a.span("refund.validate"):
        pass
    assert "refund.validate" in a.observed_spans


def test_coverage_reports_missing_rather_than_silence() -> None:
    """A service with unemitted spans must say so, not report clean."""
    a = Assurance("test", export=False)
    with a.span("refund.validate"):
        pass
    cov = a.coverage()
    assert not cov["complete"]
    assert "refund.issue" in cov["missing"]


def test_manifest_carries_work_item_id() -> None:
    """The traceability chain starts here: story id -> span attribute."""
    assert Assurance("test", export=False).manifest.work_item_id is not None
