"""Rule-based semantic type detection for dataset columns.

detect_semantic_type(column_name, values) returns a dict with:
    semantic_type, confidence, evidence, alternatives, sensitive, status

Column names are split into whole-word tokens (BusinessEntityID -> business,
entity, id), so "Manager" no longer matches "age" and "Overtime" no longer
matches "time". Values are also checked (emails, phones, dates, percentages,
currency, 0/1 flags, free text), so detection still works when a column name
gives no hint.
"""
import re
from datetime import time as dt_time

import pandas as pd

STATUS = "Proposed, pending verification"

ID_TOKENS = {"id", "key", "guid", "uuid"}
EMAIL_TOKENS = {"email", "mail"}
PHONE_TOKENS = {"phone", "mobile", "telephone", "fax", "cell"}
PERCENT_TOKENS = {"percent", "percentage", "pct"}
DATE_TOKENS = {"date", "datetime", "timestamp", "dob"}
NOT_DATE_WORDS = {"update", "candidate", "validate", "mandate"}
FLAG_TOKENS = {"flag", "is", "has"}
CATEGORY_TOKENS = {
    "gender", "sex", "status", "category", "type", "frequency", "flag",
    "level", "group", "groupname", "department", "shift", "title",
    "jobtitle", "marital", "maritalstatus", "class", "segment", "region",
    "country", "city", "state", "grade", "tier",
}
FINANCIAL_TOKENS = {
    "salary", "amount", "revenue", "price", "rate", "cost", "pay", "wage",
    "income", "balance", "fee", "tax", "profit", "spend", "budget",
    "charge", "payment",
}
NUMERIC_TOKENS = {
    "hours", "age", "count", "quantity", "qty", "score", "total", "weight",
    "height", "duration", "days", "units", "length", "distance",
    "temperature", "glucose", "bmi", "pressure", "tickets", "orders",
    "visits", "year", "years", "months", "size", "sqft", "bedrooms",
    "bathrooms", "rooms", "rating", "ratings",
}
TEXT_TOKENS = {
    "resume", "description", "comment", "comments", "notes", "note",
    "remarks", "summary", "text", "feedback",
}
SENSITIVE_TOKENS = {
    "email", "mail", "phone", "mobile", "telephone", "fax", "address",
    "birth", "dob", "national", "ssn", "aadhaar", "aadhar", "passport",
    "login", "resume", "gender", "sex", "marital", "religion", "race",
    "ethnicity", "salary", "wage",
}
PERSON_NAME_PARTS = {"first", "last", "full", "middle", "surname"}
BOOLEAN_TEXT = {"y", "n", "yes", "no", "true", "false"}

EMAIL_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"
PERCENT_PATTERN = r"-?\d+(\.\d+)?\s*%"
CURRENCY_PATTERN = r"[$\u20ac\u00a3\u20b9]\s*-?[\d,]+(\.\d+)?"
TIME_PATTERN = r"\d{1,2}:\d{2}(:\d{2})?(\s?[AaPp][Mm])?"
DATE_PATTERN = (
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?)?"
    r"(Z|[+-]\d{2}:?\d{2})?"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    r"|\d{1,2}[ ,\-]+[A-Za-z]{3,9}[ ,\-]+\d{2,4})"
)


def tokenize(column_name):
    """Split a column name into lowercase whole words."""
    text = re.sub(r"[_.\-\s]+", " ", str(column_name))
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", text)
    return [part.lower() for part in parts]


def _looks_like_phone(text):
    digits = re.sub(r"\D", "", text)
    return (
        bool(re.fullmatch(r"\+?[\d\s().\-]{7,}", text))
        and 7 <= len(digits) <= 15
        and bool(re.search(r"[\s().\-+]", text))
        and not re.fullmatch(r"-?\d+\.\d+", text)
        and not re.fullmatch(DATE_PATTERN, text)
    )


def detect_semantic_type(column_name, values):
    tokens = tokenize(column_name)
    token_set = set(tokens)
    joined = "".join(tokens)
    series = pd.Series(list(values)).dropna()
    n = len(series)

    def result(semantic_type, confidence, evidence, alternatives=None):
        sensitive = (
            bool(token_set & SENSITIVE_TOKENS)
            or ("name" in token_set and bool(token_set & PERSON_NAME_PARTS))
            or semantic_type in {"email", "phone"}
        )
        return {
            "semantic_type": semantic_type,
            "confidence": confidence,
            "evidence": evidence,
            "alternatives": alternatives or [],
            "sensitive": sensitive,
            "status": STATUS,
        }

    # What do the values look like?
    is_bool = n > 0 and pd.api.types.is_bool_dtype(series)
    numeric = (
        n > 0
        and pd.api.types.is_numeric_dtype(series)
        and not is_bool
    )
    sample = None
    if n > 0 and series.map(lambda v: isinstance(v, str)).mean() >= 0.8:
        sample = series.astype(str).str.strip().head(200)

    def share(pattern):
        return float(sample.str.fullmatch(pattern).mean())

    numeric_or_empty = n == 0 or numeric

    # 1. Email
    if token_set & EMAIL_TOKENS:
        return result("email", 0.99, "Column name contains an email word.",
                      ["text"])
    if sample is not None and share(EMAIL_PATTERN) >= 0.8:
        return result("email", 0.95,
                      "Most values match an email pattern.", ["text"])

    # 2. Percentage
    if token_set & PERCENT_TOKENS:
        return result("percentage", 0.95,
                      "Column name indicates a percentage.",
                      ["numerical_measure"])
    if sample is not None and share(PERCENT_PATTERN) >= 0.8:
        return result("percentage", 0.90,
                      "Most values contain a percentage sign.",
                      ["categorical", "numerical_measure"])

    # 3. Date
    if n > 0 and pd.api.types.is_datetime64_any_dtype(series):
        return result("date", 0.99, "Values are datetime data.", ["text"])
    name_says_date = any(
        t in DATE_TOKENS
        or (t.endswith("date") and len(t) > 4 and t not in NOT_DATE_WORDS)
        for t in tokens
    )
    if name_says_date:
        return result("date", 0.95,
                      "Column name contains a date word.", ["text"])
    if sample is not None and share(DATE_PATTERN) >= 0.8:
        return result("date", 0.90,
                      "Most values match a date pattern.", ["text"])

    # 4. Time of day
    if "time" in token_set:
        return result("time", 0.95,
                      "Column name contains the word 'time'.", ["text"])
    if n > 0 and all(isinstance(v, dt_time) for v in series):
        return result("time", 0.95, "Values are time-of-day objects.",
                      ["text"])
    if sample is not None and share(TIME_PATTERN) >= 0.8:
        return result("time", 0.90,
                      "Most values look like times of day.", ["text"])

    # 5. Phone
    if token_set & PHONE_TOKENS:
        return result("phone", 0.95,
                      "Column name indicates a phone number.",
                      ["identifier", "text"])
    if sample is not None and sample.map(_looks_like_phone).mean() >= 0.8:
        return result("phone", 0.85,
                      "Most values look like phone numbers.",
                      ["identifier", "text"])

    # 6. Identifier
    if (
        token_set & ID_TOKENS
        or any(t.endswith("guid") for t in tokens)
    ):
        return result("identifier", 0.99,
                      "Column name indicates an ID, key or GUID.",
                      ["categorical"])
    if tokens and tokens[-1] == "number":
        return result("identifier", 0.80,
                      "Column name ends with 'number' (account/serial type).",
                      ["numerical_measure", "categorical"])

    # 7. Yes/No or 0/1 flags (by values)
    if is_bool:
        return result("boolean_flag", 0.95, "Values are True/False.",
                      ["categorical"])
    if numeric:
        unique_values = set(series.unique().tolist())
        if unique_values <= {0, 1} and (
            len(unique_values) == 2 or token_set & FLAG_TOKENS
        ):
            return result("boolean_flag", 0.90,
                          "Values are only 0 and 1.",
                          ["categorical"])
    elif sample is not None:
        lowered = set(sample.str.lower().unique().tolist())
        if lowered <= BOOLEAN_TEXT and (
            len(lowered) == 2 or token_set & FLAG_TOKENS
        ):
            return result("boolean_flag", 0.85,
                          "Values are only yes/no style answers.",
                          ["categorical"])

    # 8. Categorical by name
    if token_set & CATEGORY_TOKENS or any(
        word in joined
        for word in ("jobtitle", "maritalstatus", "groupname", "payfrequency")
    ):
        return result("categorical", 0.95,
                      "Column name matches a known categorical field.",
                      ["numerical_measure"] if numeric else ["text"])
    if tokens == ["name"]:
        return result("categorical", 0.70,
                      "Generic name field; meaning depends on context.",
                      ["text", "identifier"])
    if "name" in token_set:
        return result("text", 0.70,
                      "Column name indicates a name (free text).",
                      ["identifier", "categorical"])

    # 9. Currency values and financial names
    if sample is not None and share(CURRENCY_PATTERN) >= 0.8:
        return result("financial_amount", 0.90,
                      "Most values have a currency symbol.",
                      ["numerical_measure"])
    if numeric_or_empty and token_set & FINANCIAL_TOKENS:
        return result("financial_amount", 0.90,
                      "Column name suggests a financial amount or rate.",
                      ["numerical_measure"])

    # 10. Numeric measures by name
    if numeric_or_empty and token_set & NUMERIC_TOKENS:
        return result("numerical_measure", 0.90,
                      "Column name indicates a measurable quantity.",
                      ["categorical"])

    # 11. Free text
    if token_set & TEXT_TOKENS:
        return result("text", 0.95,
                      "Column name indicates free-form text.",
                      ["categorical"])
    if sample is not None and (
        sample.str.len().mean() > 60 or sample.str.contains("<").mean() > 0.5
    ):
        return result("text", 0.85,
                      "Values are long strings or markup.",
                      ["categorical"])

    # 12. Fallbacks from the values
    if n == 0:
        return result("unknown", 0.30,
                      "No non-null values and no name rule matched.",
                      ["text", "categorical"])
    if numeric:
        whole = bool((series % 1 == 0).all())
        if whole and n >= 10 and series.is_unique:
            ordered = series.astype("int64").sort_values()
            if ordered.diff().dropna().eq(1).all():
                return result("identifier", 0.65,
                              "Unique consecutive whole numbers.",
                              ["numerical_measure"])
        if whole and series.nunique() <= 10:
            return result("categorical", 0.55,
                          "Few distinct whole numbers; name is inconclusive.",
                          ["numerical_measure"])
        return result("numerical_measure", 0.60,
                      "Numeric values; name is inconclusive.",
                      ["identifier", "categorical"])
    if sample is not None:
        if series.nunique() <= max(20, int(0.05 * n)):
            return result("categorical", 0.65,
                          "Text with few distinct values.", ["text"])
        return result("text", 0.50,
                      "Text with many distinct values.",
                      ["identifier", "categorical"])

    return result("unknown", 0.50,
                  "No semantic rule matched the name or the values.",
                  ["text", "categorical"])
