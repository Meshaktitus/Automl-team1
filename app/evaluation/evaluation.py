from dataclasses import dataclass
from typing import Any

from .metrics import Metric


@dataclass
class EvaluationResult:
    """
    Stores the result of an evaluation metric.
    """

    metric_name: str
    value: Any


class Evaluation:
    """
    Main evaluation module responsible for running metrics.
    """

    def __init__(self):
        self.metrics = []

    def add_metric(self, metric: Metric):
        """
        Add a metric to the evaluation process.
        """
        self.metrics.append(metric)

    def evaluate(self, y_true, y_pred, y_score=None):
        """
        Run all registered metrics.
        """

        results = []

        for metric in self.metrics:
            value = metric.calculate(
                y_true,
                y_pred,
                y_score
            )

            result = EvaluationResult(
                metric_name=metric.name,
                value=value
            )

            results.append(result)

        return results