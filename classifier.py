"""Rule-based Smart Attention Classification.

The category is decided by plain Python rules, NOT by the AI model, so the
same input always gives the same result.
"""


def classify_result(value, lower_range, upper_range, flag=""):
    flag = (flag or "").lower().strip()

    # 1. A laboratory "critical" flag always wins.
    if "critical" in flag or flag in ("hh", "ll", "c"):
        return "Critical"

    # 2. A laboratory high/low flag is respected even if the range is missing.
    if "high" in flag or "low" in flag or "abnormal" in flag or flag in ("h", "l"):
        return "Attention"

    # 3. Otherwise compare the value with the reference range.
    if value is None:
        return "Unknown"

    if lower_range is None and upper_range is None:
        return "Unknown"

    # Supports one-sided ranges such as "< 200" or "> 40".
    if lower_range is not None and value < lower_range:
        return "Attention"

    if upper_range is not None and value > upper_range:
        return "Attention"

    return "Within Range"


def get_explanation(category):
    explanations = {
        "Within Range": "Your result is within the reference range provided in the report.",
        "Attention": (
            "Your result is marked high or low, or falls outside the provided "
            "reference range. Discuss it with your healthcare professional."
        ),
        "Critical": (
            "The report explicitly marks this result as critical. "
            "Seek prompt guidance from your healthcare professional."
        ),
        "Unknown": "There is not enough information in the report to classify this result.",
    }
    return explanations.get(category, "Unable to explain this result.")