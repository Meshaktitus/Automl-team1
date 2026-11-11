def validate_metric_inputs(y_true, y_pred, y_score=None, requires_score=False):
    """
    Validate common inputs before calculating a metric.
    """

    if y_true is None:
        raise ValueError("y_true cannot be None.")

    if y_pred is None:
        raise ValueError("y_pred cannot be None.")

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length.")

    if requires_score and y_score is None:
        raise ValueError("This metric requires score/probability values.")

    if y_score is not None and len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length.")

    return True