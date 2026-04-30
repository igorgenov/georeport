import json

from google import genai
from google.genai import types

ARTICLE_KEYWORDS = {
    "blog", "article", "post", "news", "story", "guide", "tutorial",
    "how to", "review", "opinion", "editorial", "report",
}
PRODUCT_KEYWORDS = {
    "product", "buy", "price", "shop", "store", "order", "cart",
    "pricing", "purchase", "deal", "discount", "checkout",
}
ORGANIZATION_KEYWORDS = {
    "about us", "our team", "company", "organization", "mission",
    "careers", "contact us", "founded", "who we are", "leadership",
}


def _detect_schema_type(headings: list, title: str) -> str:
    corpus = " ".join(h["text"].lower() for h in headings) + " " + title.lower()

    scores = {
        "Article": sum(1 for kw in ARTICLE_KEYWORDS if kw in corpus),
        "Product": sum(1 for kw in PRODUCT_KEYWORDS if kw in corpus),
        "Organization": sum(1 for kw in ORGANIZATION_KEYWORDS if kw in corpus),
    }

    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        return "WebPage"

    return best_type


def _build_prompt(schema_type: str, title: str, meta_description: str, headings: list, url: str) -> str:
    headings_text = "\n".join(
        f"  - [{h['level'].upper()}] {h['text']}" for h in headings[:5]
    ) or "  (no headings found)"

    return f"""Generate a valid JSON-LD structured data block for a webpage with schema type "{schema_type}".

Page information:
- Title: {title or '(not available)'}
- Meta Description: {meta_description or '(not available)'}
- URL: {url}
- Key Headings:
{headings_text}

Rules:
1. Return ONLY a valid JSON object -- no markdown, no explanation, no extra text.
2. Use "https://schema.org" as the @context.
3. Use "{schema_type}" as the @type.
4. Include all relevant properties (name, description, url, image, etc.) filled with realistic values.
5. Base image URLs on the domain if not explicitly known."""


def _build_fallback_schema(title: str, meta_description: str, url: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title or "Untitled Page",
        "description": meta_description or "No description available.",
        "url": url,
    }


def generate_schema(page_data: dict, url: str, api_key: str) -> dict:
    title = page_data.get("title", "")
    meta_description = page_data.get("meta_description", "")
    headings = page_data.get("headings", [])

    schema_type = _detect_schema_type(headings, title)
    prompt = _build_prompt(schema_type, title, meta_description, headings, url)

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text = response.text.strip()
        result = json.loads(raw_text)
        if not isinstance(result, dict):
            raise ValueError(f"Expected JSON object, got {type(result).__name__}")

        return result

    except Exception:
        return _build_fallback_schema(title, meta_description, url)
