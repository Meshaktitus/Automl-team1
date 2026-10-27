
from pathlib import Path
import joblib
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_FILE = PROJECT_DIR / "automl_results" / "best_automl_model.joblib"


def main():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Saved model not found: {MODEL_FILE}\n"
            "Run model_training_evaluation.py first."
        )

    model = joblib.load(MODEL_FILE)

    print("\n=== Employee Leave Prediction ===")
    print("Enter 'exit' to stop.")

    while True:
        job_title = input("\nEnter employee JobTitle: ").strip()

        if job_title.lower() == "exit":
            print("Prediction program closed.")
            break

        if not job_title:
            print("Please enter a job title.")
            continue

        input_data = pd.DataFrame({
            "JobTitle": [job_title]
        })

        prediction = model.predict(input_data)

        vacation_hours = prediction[0][0]
        sick_leave_hours = prediction[0][1]

        print("\nPredicted results")
        print(f"JobTitle: {job_title}")
        print(f"VacationHours: {vacation_hours:.2f}")
        print(f"SickLeaveHours: {sick_leave_hours:.2f}")

        print(
            "\nNote: These are estimates based only on JobTitle."
        )


if __name__ == "__main__":
    main()
