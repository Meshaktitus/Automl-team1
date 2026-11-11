
import pytest

from app.evaluation.evaluation import Evaluation
from app.evaluation.classification_metrics import (
    AccuracyMetric,
    PrecisionMetric,
    RecallMetric,
    F1Metric,
)


def test_classification_metrics():
    evaluation = Evaluation()

    evaluation.add_metric(AccuracyMetric())
    evaluation.add_metric(PrecisionMetric())
    evaluation.add_metric(RecallMetric())
    evaluation.add_metric(F1Metric())

    results = evaluation.evaluate(
        [1, 0, 1, 1, 0],
        [1, 1, 0, 1, 0]
    )

    assert len(results) == 4

    assert results[0].metric_name == "accuracy"
    assert results[0].value == pytest.approx(0.6)

    assert results[1].metric_name == "precision"
    assert results[1].value == pytest.approx(2 / 3)

    assert results[2].metric_name == "recall"
    assert results[2].value == pytest.approx(2 / 3)

    assert results[3].metric_name == "f1"
    assert results[3].value == pytest.approx(2 / 3)