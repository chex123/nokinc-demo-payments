from pathlib import Path

import pytest

from payments.assurance import Assurance, UndeclaredSpan


def test_declared_span_is_recorded(tmp_path: Path) -> None:
    contract = tmp_path / "spans.yaml"
    contract.write_text("spans: [refund.validate]\nmetrics: []\n")
    assurance = Assurance("test-service", str(contract), export=False)

    with assurance.span("refund.validate", order_id="o-1"):
        pass

    assert assurance.coverage()["observed"] == 1
    assert assurance.coverage()["complete"] is True


def test_undeclared_span_fails_closed(tmp_path: Path) -> None:
    contract = tmp_path / "spans.yaml"
    contract.write_text("spans: [refund.validate]\nmetrics: []\n")
    assurance = Assurance("test-service", str(contract), export=False)

    with pytest.raises(UndeclaredSpan), assurance.span("refund.issue"):
        pass
