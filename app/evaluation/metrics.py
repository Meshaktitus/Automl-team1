from abc import ABC, abstractmethod


class Metric(ABC):
    """
    Base interface for all evaluation metrics.
    """

    name: str
    problem_type: str
    direction: str
    requires_score: bool = False

    @abstractmethod
    def calculate(self, y_true, y_pred, y_score=None):
        """
        Calculate the metric value.

        Parameters:
            y_true: Actual/true values.
            y_pred: Predicted values.
            y_score: Optional probability/score values.

        Returns:
            Calculated metric value.
        """
        raise NotImplementedError