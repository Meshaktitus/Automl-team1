from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
    mean_absolute_percentage_error
)
from .metric_types import RegressionMetric


class MAEMetric(RegressionMetric):
    """
    Mean Absolute Error metric for regression models.
    """

    name = "mae"
    direction = "minimize"

    def calculate(self, y_true, y_pred, y_score=None):
        return mean_absolute_error(y_true, y_pred)

class RMSEMetric(RegressionMetric):
    """
    Root Mean Squared Error metric for regression models.
    """

    name = "rmse"
    direction = "minimize"

    def calculate(self, y_true, y_pred, y_score=None):
        return root_mean_squared_error(y_true, y_pred)

class R2Metric(RegressionMetric):
    """
    R-squared metric for regression models.
    """

    name = "r2"
    direction = "maximize"

    def calculate(self, y_true, y_pred, y_score=None):
        return r2_score(y_true, y_pred)

class MAPEMetric(RegressionMetric):
    """
    Mean Absolute Percentage Error metric for regression models.
    """

    name = "mape"
    direction = "minimize"

    def calculate(self, y_true, y_pred, y_score=None):
        return mean_absolute_percentage_error(y_true, y_pred)