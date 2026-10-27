from datetime import time

import pandas as pd
import pytest

from semantic_rules import detect_semantic_type, tokenize

MANY = ["alpha", "beta", "gamma"] * 10


def kind(name, values):
    return detect_semantic_type(name, values)["semantic_type"]


def test_tokenize_splits_camel_case_and_acronyms():
    assert tokenize("BusinessEntityID") == ["business", "entity", "id"]
    assert tokenize("NationalIDNumber") == ["national", "id", "number"]
    assert tokenize("pct_complete") == ["pct", "complete"]


def test_result_has_all_keys():
    result = detect_semantic_type("Age", [20, 30])
    assert set(result) == {
        "semantic_type", "confidence", "evidence",
        "alternatives", "sensitive", "status",
    }


# Bugs found in the old rules: words hidden inside other words
@pytest.mark.parametrize("name, values, expected", [
    ("Manager", MANY, "categorical"),
    ("AccountNumber", ["A1001", "A1002", "A1003"], "identifier"),
    ("Overtime", [1.5, 2.5, 3.5, 4.5], "numerical_measure"),
    ("Corporate", MANY, "categorical"),
])
def test_old_substring_bugs_are_fixed(name, values, expected):
    assert kind(name, values) == expected


@pytest.mark.parametrize("name, values, expected", [
    ("BusinessEntityID", [1, 2, 3], "identifier"),
    ("rowguid", ["F01251E5-96A3"], "identifier"),
    ("NationalIDNumber", [295847284, 245797967], "identifier"),
    ("Rate", [63.46, 43.27, 125.5], "financial_amount"),
    ("VacationHours", [99, 1, 2, 40], "numerical_measure"),
    ("JobTitle", MANY, "categorical"),
    ("PayFrequency", [1, 2, 2, 1], "categorical"),
    ("Gender", ["M", "F", "M"], "categorical"),
    ("Resume", ["<ns:Resume>" + "x" * 80 + "</ns:Resume>"] * 3, "text"),
])
def test_hr_style_columns(name, values, expected):
    assert kind(name, values) == expected


def test_value_based_phone_detection():
    values = ["425-555-0111", "206-555-0198", "425-555-0155"]
    assert kind("contact", values) == "phone"


def test_value_based_email_detection():
    assert kind("contact_info", ["a@x.com", "b@y.org", "c@z.net"]) == "email"


def test_percentage_from_values_and_name():
    assert kind("pct_complete", ["85%", "90%"]) == "percentage"
    assert kind("progress", ["85%", "90%", "12.5%"]) == "percentage"


def test_dates_from_dtype_name_and_values():
    assert kind("BirthDate", list(pd.to_datetime(["1969-01-29"]))) == "date"
    assert kind("HireDate", ["x", "y"]) == "date"
    assert kind("joined", ["2020-01-05", "2021-03-10"]) == "date"


def test_time_of_day():
    assert kind("StartTime", [time(7, 0), time(15, 0)]) == "time"
    assert kind("opening", ["07:00:00", "15:00:00", "23:00:00"]) == "time"


def test_boolean_flags():
    assert kind("CurrentFlag", [1, 0, 1, 1, 0]) == "boolean_flag"
    assert kind("is_active", ["Y", "N", "Y"]) == "boolean_flag"
    assert kind("opted_in", [True, False, True]) == "boolean_flag"


def test_currency_values():
    assert kind("figure", ["$1,200", "$300.50", "$45"]) == "financial_amount"


def test_sequential_numbers_are_identifiers():
    assert kind("row", list(range(1, 21))) == "identifier"


def test_empty_column_is_unknown():
    assert kind("mystery", []) == "unknown"


def test_sensitive_columns_are_flagged():
    assert detect_semantic_type("NationalIDNumber", [1, 2])["sensitive"]
    assert detect_semantic_type("Resume", ["text"])["sensitive"]
    assert detect_semantic_type("email", ["a@b.com"])["sensitive"]
    assert not detect_semantic_type("VacationHours", [1, 2])["sensitive"]


def test_rating_column_is_a_numeric_measure():
    assert kind("rating", [1, 2, 3, 4, 5, 3, 4, 5, 2, 1]) == (
        "numerical_measure")
