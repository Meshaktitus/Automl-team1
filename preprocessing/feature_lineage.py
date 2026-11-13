from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "docs" / "feature_lineage.json"


def build_feature_lineage():
    """Build provisional lineage records for reviewed HR dataset columns."""

    records = [
        {
            "source_column": "JobTitle",
            "transformation": "One-hot encoding",
            "output_feature": [
                "JobTitle_<category>"
            ],
            "purpose": "Represent job titles as binary model input features",
            "status": "Prototype - requires modeling review",
            "notes": (
                "67 distinct categories were observed in the current dataset. "
                "The actual output columns depend on the categories and "
                "encoder configuration. Review rare-category grouping and "
                "fit encoding on training data only during model development."
            ),
        },
        {
            "source_column": "VacationHours",
            "transformation": "None in lineage prototype",
            "output_feature": "VacationHours",
            "purpose": "Provisional regression target candidate",
            "status": "Pending team confirmation",
            "notes": (
                "Keep as a target candidate until the modeling objective "
                "is confirmed. Exclude it from model inputs whenever it is "
                "the selected target."
            ),
        },
        {
            "source_column": "SickLeaveHours",
            "transformation": "None in lineage prototype",
            "output_feature": "SickLeaveHours",
            "purpose": "Provisional regression target candidate",
            "status": "Pending team confirmation",
            "notes": (
                "Keep as a target candidate until the modeling objective "
                "is confirmed. Exclude it from model inputs whenever it is "
                "the selected target."
            ),
        },
        {
            "source_column": "CurrentFlag",
            "transformation": "Constant-column assessment",
            "output_feature": None,
            "purpose": "Feature usefulness review",
            "status": "Review",
            "notes": (
                "Only one unique value was observed in the current dataset. "
                "Assess usefulness before including this column in a model."
            ),
        },
        {
            "source_column": "BusinessEntityID",
            "transformation": "Identifier review",
            "output_feature": None,
            "purpose": "Potential record identifier",
            "status": "Review",
            "notes": (
                "Do not automatically use as a predictive feature. "
                "Confirm its role with the project team."
            ),
        },
        {
            "source_column": "NationalIDNumber",
            "transformation": "Identifier review",
            "output_feature": None,
            "purpose": "Potential personal identifier",
            "status": "Review",
            "notes": (
                "Exclude from model inputs unless explicitly justified "
                "and approved."
            ),
        },
        {
            "source_column": "LoginID",
            "transformation": "Identifier review",
            "output_feature": None,
            "purpose": "Potential account identifier",
            "status": "Review",
            "notes": (
                "Do not automatically use as a predictive feature. "
                "Confirm its role with the project team."
            ),
        },
        {
            "source_column": "rowguid",
            "transformation": "Identifier review",
            "output_feature": None,
            "purpose": "Row identifier",
            "status": "Review",
            "notes": (
                "Do not automatically use as a predictive feature."
            ),
        },
    ]

    return records


def main():
    records = build_feature_lineage()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=4, ensure_ascii=False)

    print("Feature lineage documentation generated.")
    print(f"Records: {len(records)}")
    print(f"Output: {OUTPUT_PATH}")
    print("Target and feature selection remains pending team confirmation.")


if __name__ == "__main__":
    main()