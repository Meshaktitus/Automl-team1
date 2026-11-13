from abc import ABC

from .metrics import Metric


class ClassificationMetric(Metric, ABC):
    """
    Base class for classification metrics.
    """

    problem_type = "classification"


class RegressionMetric(Metric, ABC):
    """
    Base class for regression metrics.
    """

    problem_type = "regression"


class ClusteringMetric(Metric, ABC):
    """
    Base class for clustering metrics.
    """

    problem_type = "clustering"


class ForecastingMetric(Metric, ABC):
    """
    Base class for forecasting metrics.
    """

    problem_type = "forecasting"