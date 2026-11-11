from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from .metric_types import ClassificationMetric


class AccuracyMetric(ClassificationMetric):
    """
    Accuracy metric for classification models.
    """

    name = "accuracy"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return accuracy_score(y_true, y_pred)


class PrecisionMetric(ClassificationMetric):
    """
    Precision metric for classification models.
    """

    name = "precision"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return precision_score(y_true, y_pred, zero_division=0)

class RecallMetric(ClassificationMetric):
    """
    Recall metric for classification models.
    """

    name = "recall"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return recall_score(y_true, y_pred, zero_division=0)

class F1Metric(ClassificationMetric):
    """
    F1 score metric for classification models.
    """

    name = "f1"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return f1_score(y_true, y_pred, zero_division=0)