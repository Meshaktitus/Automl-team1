from app.evaluation.metrics import Metric
from app.evaluation.evaluation import Evaluation


class DummyMetric(Metric):
    name = "dummy"
    problem_type = "classification"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return 1.0


def test_evaluation_runs_metric():
    evaluation = Evaluation()

    evaluation.add_metric(DummyMetric())

    results = evaluation.evaluate(
        [1, 0],
        [1, 0]
    )

    assert results[0].metric_name == "dummy"
    assert results[0].value == 1.0