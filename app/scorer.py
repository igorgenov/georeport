import json
import re

from bs4 import BeautifulSoup

VAGUE_HEADING_WORDS = {
    "details", "more info", "click here", "read more", "learn more",
    "info", "stuff", "things", "misc", "other", "untitled",
}


def _status_from_ratio(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.8:
        return "pass"
    elif ratio >= 0.4:
        return "partial"
    return "fail"


def score_schema_markup(soup: BeautifulSoup) -> dict:
    max_score = 30
    score = 0
    details = []

    ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not ld_scripts:
        return {
            "metric": "Schema Markup", "score": 0, "max_score": max_score,
            "status": "fail", "detail": "No JSON-LD script tag found.",
        }

    score += 8
    details.append("JSON-LD script tag found.")

    all_ld = []
    for script in ld_scripts:
        try:
            data = json.loads(script.string or "")
            all_ld.extend(data if isinstance(data, list) else [data])
        except (json.JSONDecodeError, TypeError):
            continue

    if not all_ld:
        details.append("JSON-LD content could not be parsed.")
        return {
            "metric": "Schema Markup", "score": score, "max_score": max_score,
            "status": _status_from_ratio(score, max_score), "detail": " ".join(details),
        }

    has_type = any(d.get("@type") for d in all_ld if isinstance(d, dict))
    if has_type:
        score += 7
        types_found = [str(d.get("@type")) for d in all_ld if isinstance(d, dict) and d.get("@type")]
        details.append(f"Valid @type found: {', '.join(types_found[:3])}.")
    else:
        details.append("No @type field in JSON-LD.")

    has_name = any(d.get("name") for d in all_ld if isinstance(d, dict))
    has_desc = any(d.get("description") for d in all_ld if isinstance(d, dict))
    if has_name and has_desc:
        score += 8
        details.append("'name' and 'description' fields present.")
    elif has_name:
        score += 4
        details.append("'name' present but 'description' missing.")
    elif has_desc:
        score += 4
        details.append("'description' present but 'name' missing.")
    else:
        details.append("Neither 'name' nor 'description' found.")

    has_url = any(d.get("url") for d in all_ld if isinstance(d, dict))
    has_image = any(d.get("image") for d in all_ld if isinstance(d, dict))
    if has_url and has_image:
        score += 7
        details.append("'url' and 'image' fields present.")
    elif has_url:
        score += 3
        details.append("'url' present but 'image' missing.")
    elif has_image:
        score += 3
        details.append("'image' present but 'url' missing.")
    else:
        details.append("Neither 'url' nor 'image' found.")

    return {
        "metric": "Schema Markup", "score": score, "max_score": max_score,
        "status": _status_from_ratio(score, max_score), "detail": " ".join(details),
    }


def score_semantic_html(soup: BeautifulSoup) -> dict:
    max_score = 25
    score = 0
    found, missing = [], []

    for tag in ["main", "article", "section", "nav", "aside"]:
        if soup.find(tag):
            score += 5
            found.append(f"<{tag}>")
        else:
            missing.append(f"<{tag}>")

    parts = []
    if found:
        parts.append(f"Found semantic elements: {', '.join(found)}.")
    if missing:
        parts.append(f"Missing semantic elements: {', '.join(missing)}.")

    return {
        "metric": "Semantic HTML", "score": score, "max_score": max_score,
        "status": _status_from_ratio(score, max_score), "detail": " ".join(parts),
    }


def score_image_alt_text(soup: BeautifulSoup) -> dict:
    max_score = 25
    images = soup.find_all("img")
    total = len(images)

    if total == 0:
        return {
            "metric": "Image Alt Text", "score": max_score, "max_score": max_score,
            "status": "pass", "detail": "No images found; alt text check not applicable.",
        }

    with_alt = sum(1 for img in images if img.get("alt", "").strip())
    without_alt = total - with_alt
    percentage = (with_alt / total) * 100
    score = round((with_alt / total) * max_score)

    detail = f"{with_alt}/{total} images ({percentage:.0f}%) have non-empty alt text."
    if without_alt:
        detail += f" {without_alt} image(s) missing alt."

    return {
        "metric": "Image Alt Text", "score": score, "max_score": max_score,
        "status": _status_from_ratio(score, max_score), "detail": detail,
    }


def score_content_structure(soup: BeautifulSoup) -> dict:
    max_score = 20
    score = 0
    details = []

    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")

    if len(h1s) == 1:
        score += 4
        details.append("Exactly one <h1> found.")
    elif len(h1s) == 0:
        details.append("No <h1> found.")
    else:
        details.append(f"{len(h1s)} <h1> tags found (should be exactly 1).")

    if len(h2s) >= 2:
        score += 4
        details.append(f"Found {len(h2s)} <h2> tags (>=2 required).")
    elif len(h2s) == 1:
        score += 2
        details.append("Only 1 <h2>; at least 2 recommended.")
    else:
        details.append("No <h2> tags found.")

    if len(h3s) >= 1:
        score += 4
        details.append(f"Found {len(h3s)} <h3> tag(s).")
    else:
        details.append("No <h3> tags found; use them to break content into sub-sections.")

    all_headings = soup.find_all(re.compile(r"^h[1-6]$"))
    levels = [int(h.name[1]) for h in all_headings]
    skipped = any(
        levels[i] > levels[i - 1] + 1
        for i in range(1, len(levels))
    )
    if not skipped:
        score += 4
        details.append("No skipped heading levels detected.")
    else:
        details.append("Skipped heading levels detected (e.g., h1 -> h3).")

    heading_texts = [h.get_text(strip=True).lower() for h in soup.find_all(["h1", "h2", "h3"])]
    vague = [t for t in heading_texts if t in VAGUE_HEADING_WORDS]
    if not vague:
        score += 4
        details.append("All headings are descriptive and specific.")
    else:
        details.append(f"Vague heading(s): {', '.join(repr(v) for v in vague[:3])}.")

    return {
        "metric": "Content Structure", "score": score, "max_score": max_score,
        "status": _status_from_ratio(score, max_score), "detail": " ".join(details),
    }


def compute_geo_grade(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def generate_recommendations(metrics: list) -> list:
    recommendation_map = {
        "Schema Markup": (
            "Add a complete JSON-LD block with @type, name, description, url, and image. "
            "This is the single most impactful change for AI citation readiness."
        ),
        "Semantic HTML": (
            "Wrap your page content in semantic HTML5 elements like <main>, <article>, <section>, <nav>, and <aside>. "
            "AI parsers rely on these to understand content structure."
        ),
        "Image Alt Text": (
            "Add descriptive, keyword-rich alt attributes to all <img> tags. "
            "AI engines use alt text to understand and cite visual content."
        ),
        "Content Structure": (
            "Restructure your headings to have exactly one <h1>, at least two <h2>s, and at least one <h3>. "
            "Avoid skipping heading levels and use specific, keyword-rich text."
        ),
    }

    sorted_metrics = sorted(
        metrics,
        key=lambda m: m["score"] / m["max_score"] if m["max_score"] > 0 else 0,
    )

    return [
        recommendation_map.get(m["metric"], f"Improve your {m['metric']} score.")
        for m in sorted_metrics[:3]
    ]


def run_scoring(soup: BeautifulSoup) -> dict:
    metrics = [
        score_schema_markup(soup),
        score_semantic_html(soup),
        score_image_alt_text(soup),
        score_content_structure(soup),
    ]

    geo_score = sum(m["score"] for m in metrics)
    geo_grade = compute_geo_grade(geo_score)
    recommendations = generate_recommendations(metrics)

    return {
        "metrics": metrics,
        "geo_score": geo_score,
        "geo_grade": geo_grade,
        "recommendations": recommendations,
    }
