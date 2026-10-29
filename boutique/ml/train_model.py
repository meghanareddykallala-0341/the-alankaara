from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "alankaara_training_dataset_v1.csv"
MODEL_FILE = BASE_DIR / "alankaara_model.joblib"

FEATURES = [
    "category",
    "price_inr",
    "product_colour",
    "product_style",
    "fabric",
    "occasion_tags",
    "weather_suitability",
    "user_occasion",
    "user_budget_max_inr",
    "user_weather",
    "user_preferred_style",
    "user_preferred_colour",
]

TARGET = "label"


def main():
    # 1. Check that the dataset exists.
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATA_FILE}"
        )

    # 2. Load the dataset.
    df = pd.read_csv(DATA_FILE)

    # 3. Check required columns.
    required_columns = FEATURES + [TARGET]
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    # 4. Remove rows without a target label.
    df = df.dropna(subset=[TARGET]).copy()

    if len(df) < 10:
        raise ValueError(
            "The dataset is too small to train and evaluate reliably."
        )

    # Keep target labels consistent.
    df[TARGET] = df[TARGET].astype(str).str.strip()

    if df[TARGET].nunique() < 2:
        raise ValueError(
            "The dataset must contain at least two different labels."
        )

    # 5. Separate input features and target.
    X = df[FEATURES].copy()
    y = df[TARGET].copy()

    # Clean categorical features and prepare numeric features.
    categorical_features = X.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    numeric_features = [
        column
        for column in FEATURES
        if column not in categorical_features
    ]

    for column in categorical_features:
        X[column] = X[column].fillna("Unknown").astype(str).str.strip()

    for column in numeric_features:
        X[column] = pd.to_numeric(X[column], errors="coerce")

    # Stratification requires enough examples for each label.
    label_counts = y.value_counts()

    if label_counts.min() < 2:
        raise ValueError(
            "Each label needs at least two rows for a stratified split."
        )

    # 6. Prepare preprocessing.
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "encoder",
            OneHotEncoder(handle_unknown="ignore"),
        ),
    ])

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    preprocessor = ColumnTransformer([
        ("categorical", categorical_pipeline, categorical_features),
        ("numeric", numeric_pipeline, numeric_features),
    ])

    # 7. Build the Random Forest model.
    model = Pipeline([
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced",
            ),
        ),
    ])

    # 8. Split the dataset into training and test sets.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # 9. Train the model.
    print("Training Alankaara recommendation model...")
    model.fit(X_train, y_train)

    # 10. Evaluate on the held-out test set.
    predictions = model.predict(X_test)

    print("\n--- Model Evaluation ---")
    print("Total dataset rows:", len(df))
    print("Training rows:", len(X_train))
    print("Test rows:", len(X_test))
    print("Label counts:")
    print(y.value_counts().to_string())

    print(
        "\nAccuracy:",
        round(accuracy_score(y_test, predictions), 3),
    )

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print("Confusion matrix:")
    print(
        confusion_matrix(
            y_test,
            predictions,
            labels=model.classes_,
        )
    )
    print("Label order:", list(model.classes_))

    # 11. Save the model for Django to use.
    joblib.dump(model, MODEL_FILE)

    print(f"\nModel saved to: {MODEL_FILE}")
    print(
        "\nImportant: the dataset uses synthetic labels. "
        "These metrics are a baseline, not proof of real-world "
        "recommendation quality."
    )


if __name__ == "__main__":
    main()