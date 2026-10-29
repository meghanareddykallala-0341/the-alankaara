from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings


MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "boutique"
    / "ml"
    / "alankaara_model.joblib"
)

CATALOG_PATH = (
    Path(settings.BASE_DIR)
    / "boutique"
    / "ml"
    / "data"
    / "alankaara_product_catalog_seed_v1.csv"
)

FEATURE_COLUMNS = [
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

CATEGORY_MAP = {
    "sarees": "Saree",
    "lehengas": "Lehenga",
    "anarkalis": "Anarkali",
    "kurtis": "Kurti",
    "coord-sets": "Coord set",
    "indo-western": "Indo-western",
    "dupattas": "Dupatta",
    "jewellery": "Jewellery",
    "footwear": "Footwear",
    "handbags": "Handbag",
    "blouses": "Blouse",
}

OCCASION_MAP = {
    "daily": "Casual",
    "college": "College",
    "office": "Office",
    "festive": "Festive",
    "wedding": "Wedding",
    "party": "Party",
}

STYLE_MAP = {
    "traditional": "Traditional",
    "modern": "Contemporary ethnic",
    "casual": "Everyday ethnic",
    "elegant": "Elegant",
    "any": "Any",
}

_model = None
_catalog = None


def get_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def get_catalog():
    global _catalog

    if _catalog is None:
        if not CATALOG_PATH.exists():
            _catalog = pd.DataFrame()
        else:
            _catalog = pd.read_csv(CATALOG_PATH)

            if "product_name" in _catalog.columns:
                _catalog["product_name_key"] = (
                    _catalog["product_name"]
                    .astype(str)
                    .str.strip()
                    .str.casefold()
                )

    return _catalog


def normalize_colour(value):
    """Normalize common colour names for comparisons."""
    if value is None:
        return ""

    value = str(value).strip().casefold()

    if value in {"", "unknown", "nan", "none"}:
        return ""

    aliases = {
        "pink": {
            "pink", "light pink", "hot pink", "rose pink",
            "rose", "blush", "rani",
        },
        "red": {"red", "dark red", "crimson", "scarlet"},
        "blue": {
            "blue", "navy", "navy blue", "royal blue", "sky blue",
        },
        "green": {
            "green", "dark green", "olive", "sage green",
            "emerald", "mint",
        },
        "yellow": {"yellow", "mustard", "mustard yellow"},
        "black": {"black"},
        "white": {"white", "ivory", "off-white", "off white", "cream"},
        "maroon": {"maroon", "wine", "burgundy"},
        "gold": {"gold", "golden"},
    }

    for standard_colour, variations in aliases.items():
        if value in variations:
            return standard_colour

    return value


def colour_matches(product_colour, preferred_colour):
    """Return whether a product matches the requested colour."""
    preferred = normalize_colour(preferred_colour)

    if not preferred or preferred == "any":
        return True

    actual = normalize_colour(product_colour)

    if not actual:
        return False

    return actual == preferred


def text_matches(actual, preferred):
    """Compare text while treating Any and Unknown as non-restrictive."""
    actual = str(actual or "").strip().casefold()
    preferred = str(preferred or "").strip().casefold()

    if preferred in {"", "any", "unknown"}:
        return True

    if actual in {"", "unknown", "nan", "none"}:
        return False

    return actual == preferred


def get_catalogue_values(product, catalog):
    """Get catalogue information, falling back to product data."""
    details = {
        "product_colour": product.color or "Unknown",
        "product_style": "Unknown",
        "fabric": "Unknown",
        "occasion_tags": "Unknown",
        "weather_suitability": "Unknown",
    }

    if catalog.empty or "product_name_key" not in catalog.columns:
        return details

    product_key = product.name.strip().casefold()
    matches = catalog[
        catalog["product_name_key"] == product_key
    ]

    if matches.empty:
        return details

    item = matches.iloc[0]

    field_mapping = {
        "product_colour": "colour",
        "product_style": "style",
        "fabric": "fabric",
        "occasion_tags": "occasion_tags",
        "weather_suitability": "weather_suitability",
    }

    for field, column in field_mapping.items():
        value = item.get(column)

        if pd.notna(value) and str(value).strip().casefold() not in {
            "", "unknown", "nan", "none"
        }:
            details[field] = str(value).strip()

    return details


def calculate_match_score(
    row,
    preferred_colour,
    preferred_style,
    occasion,
    weather,
    budget,
):
    """
    Calculate a transparent preference-fit score from 0 to 100.

    This is a rule-based score, not a probability from the ML model.
    """
    points = 0
    maximum = 0

    # Colour match: 35 points when a colour is specified.
    if normalize_colour(preferred_colour) not in {"", "any"}:
        maximum += 35
        if colour_matches(
            row["product_colour"], preferred_colour
        ):
            points += 35

    # Style match: 25 points when a specific style is requested.
    if str(preferred_style).casefold() != "any":
        maximum += 25
        if text_matches(
            row["product_style"], preferred_style
        ):
            points += 25

    # Occasion match: 25 points.
    maximum += 25
    if text_matches(row["occasion_tags"], occasion):
        points += 25

    # Weather match: 15 points when the product has known suitability.
    if str(row["weather_suitability"]).casefold() not in {
        "", "unknown", "nan", "none"
    }:
        maximum += 15
        if text_matches(row["weather_suitability"], weather):
            points += 15

    if maximum == 0:
        return 100.0

    return round((points / maximum) * 100, 1)


def recommend_products(
    products,
    occasion,
    budget,
    weather="Mild",
    preferred_style="Any",
    preferred_colour="Any",
):
    model = get_model()
    catalog = get_catalog()

    occasion_key = str(occasion).strip().lower()
    style_key = str(preferred_style).strip().lower()

    user_occasion = OCCASION_MAP.get(
        occasion_key, str(occasion).title()
    )

    user_style = STYLE_MAP.get(style_key, "Any")

    user_colour = (
        "Any"
        if normalize_colour(preferred_colour) == "any"
        else str(preferred_colour).strip().title()
    )

    candidates = []

    for product in products:
        price = float(product.price)

        # Never recommend products above the budget.
        if price > float(budget):
            continue

        category = CATEGORY_MAP.get(
            product.category.lower(),
            product.category.replace("-", " ").title(),
        )

        details = get_catalogue_values(product, catalog)

        row = {
            "category": category,
            "price_inr": price,
            "product_colour": details["product_colour"],
            "product_style": details["product_style"],
            "fabric": details["fabric"],
            "occasion_tags": details["occasion_tags"],
            "weather_suitability": details["weather_suitability"],
            "user_occasion": user_occasion,
            "user_budget_max_inr": float(budget),
            "user_weather": weather,
            "user_preferred_style": user_style,
            "user_preferred_colour": user_colour,
        }

        matches_colour = colour_matches(
            row["product_colour"], user_colour
        )

        match_score = calculate_match_score(
            row=row,
            preferred_colour=user_colour,
            preferred_style=user_style,
            occasion=user_occasion,
            weather=weather,
            budget=budget,
        )

        candidates.append({
            "product": product,
            "row": row,
            "matches_colour": matches_colour,
            "match_score": match_score,
        })

    if not candidates:
        return []

    frame = pd.DataFrame(
        [item["row"] for item in candidates],
        columns=FEATURE_COLUMNS,
    )

    predictions = model.predict(frame)
    probabilities = model.predict_proba(frame)
    classes = list(model.classes_)

    if "recommended" not in classes:
        return []

    recommended_index = classes.index("recommended")
    ranked = []

    for index, item in enumerate(candidates):
        probability = float(
            probabilities[index][recommended_index]
        )

        if predictions[index] != "recommended":
            continue

        # Keep the ML probability and the preference-fit score separate.
        ranked.append({
            "product": item["product"],
            "matches_colour": item["matches_colour"],
            "match_score": item["match_score"],
            "ml_probability": probability,
        })

    # Prioritize colour, then overall preference fit, then ML probability.
    ranked.sort(
        key=lambda item: (
            item["matches_colour"],
            item["match_score"],
            item["ml_probability"],
        ),
        reverse=True,
    )

    # The existing view expects a list of Product objects.
    return [
        item["product"]
        for item in ranked[:12]
    ]
