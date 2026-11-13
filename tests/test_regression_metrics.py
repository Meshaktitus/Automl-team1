
import pytest

from app.evaluation.evaluation import Evaluation
from app.evaluation.regression_metrics import (
    MAEMetric,
    RMSEMetric,
    R2Metric,
    MAPEMetric,
)


def test_regression_metrics():
    evaluation = Evaluation()

    evaluation.add_metric(MAEMetric())
    evaluation.add_metric(RMSEMetric())
    evaluation.add_metric(R2Metric())
    evaluation.add_metric(MAPEMetric())

    results = evaluation.evaluate(
        [10, 20, 30],
        [8, 23, 27]
    )

    assert len(results) == 4

    assert results[0].metric_name == "mae"
    assert results[0].value == pytest.approx(8 / 3)

    assert results[1].metric_name == "rmse"
    assert results[1].value == pytest.approx((22 / 3) ** 0.5)

    assert results[2].metric_name == "r2"
    assert results[2].value == pytest.approx(0.89)

    assert results[3].metric_name == "mape"
    assert results[3].value == pytest.approx(
        (0.2 + 0.15 + 0.1) / 3
    )