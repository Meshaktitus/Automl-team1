import joblib
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.dummy import DummyRegressor

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "data" / "HumanResources.Employee.xlsx"
OUTPUT_DIR = PROJECT_DIR / "automl_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Demo configuration
INPUT_COLUMN = "JobTitle"
TARGET_COLUMNS = ["VacationHours", "SickLeaveHours"]

def main():
    # 1. Load the employee dataset
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}\n"
            "Check the Excel filename and data folder."
        )

    df = pd.read_excel(DATA_FILE)

    print("\nDataset loaded successfully.")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # 2. Validate required columns
    required = [INPUT_COLUMN] + TARGET_COLUMNS
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # 3. Keep only the input and target columns; remove incomplete rows
    data = df[required].dropna().copy()

    X = data[[INPUT_COLUMN]].astype(str)
    y = data[TARGET_COLUMNS].apply(pd.to_numeric, errors="coerce")

    valid_rows = y.notna().all(axis=1)
    X = X.loc[valid_rows]
    y = y.loc[valid_rows]

    if len(X) < 10:
        raise ValueError("Not enough valid rows to train and test models.")

    # 4. Split data before training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    # 5. Define candidate models
    models = {
    "Mean Baseline": DummyRegressor(strategy="mean"),
    "Linear Regression": LinearRegression(),
    "Decision Tree": DecisionTreeRegressor(random_state=42),
    "Random Forest": RandomForestRegressor(
        n_estimators=200,
        random_state=42
    ),
    }

    results = []
    trained_models = {}

    # 6. Train and evaluate each candidate
    for model_name, estimator in models.items():
        pipeline = Pipeline([
            (
                "encode",
                ColumnTransformer([
                    (
                        "jobtitle",
                        OneHotEncoder(handle_unknown="ignore"),
                        [INPUT_COLUMN],
                    )
                ]),
            ),
            ("model", estimator),
        ])

        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        trained_models[model_name] = pipeline

        for index, target in enumerate(TARGET_COLUMNS):
            actual = y_test[target].to_numpy()
            predicted = predictions[:, index]

            results.append({
                "model": model_name,
                "target": target,
                "MAE": mean_absolute_error(actual, predicted),
                "RMSE": mean_squared_error(
                    actual, predicted
                ) ** 0.5,
                "R2": r2_score(actual, predicted),
            })

    # 7. Display and save the evaluation results
    results_df = pd.DataFrame(results)
    results_df.to_csv(
        OUTPUT_DIR / "model_evaluation_results.csv", index=False
    )

    print("\nMODEL EVALUATION RESULTS")
    print(results_df.round(3).to_string(index=False))

    # 8. Choose the lowest-MAE candidate separately for each target
    print("\nLOWEST-MAE CANDIDATES (on this test split)")
    for target in TARGET_COLUMNS:
        target_results = results_df[
            results_df["target"] == target
        ].sort_values("MAE")

        print(
            f"{target}: {target_results.iloc[0]['model']} "
            f"(MAE = {target_results.iloc[0]['MAE']:.3f})"
        )
    # Select the model with the lowest average MAE across both targets
    mean_mae = results_df.groupby("model")["MAE"].mean()
    best_model_name = mean_mae.idxmin()

    # Save the selected trained pipeline
    best_model = trained_models[best_model_name]
    model_path = OUTPUT_DIR / "best_automl_model.joblib"
    joblib.dump(best_model, model_path)

    # Save the selected model name
    selection_path = OUTPUT_DIR / "selected_model.txt"
    selection_path.write_text(
        f"Selected model: {best_model_name}\n"
        f"Selection rule: Lowest average MAE across both targets\n",
        encoding="utf-8"
    )

    print(f"\nSelected model: {best_model_name}")
    print(f"Saved model to: {model_path}")
    print(f"Saved selection details to: {selection_path}")
    print(f"\nResults saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
