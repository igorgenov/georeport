import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def fetch_page(url: str) -> tuple[str, str]:
    try:
        with httpx.Client(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPError(504, f"Timed out after 10s fetching {url}.")
    except httpx.ConnectError:
        raise HTTPError(502, f"Could not connect to {url}.")
    except httpx.HTTPStatusError as exc:
        raise HTTPError(502, f"Received HTTP {exc.response.status_code} from {url}.")
    except httpx.HTTPError as exc:
        raise HTTPError(502, f"Failed to fetch {url}: {exc}")

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise HTTPError(422, f"Non-HTML content (Content-Type: {content_type}).")

    return response.text, str(response.url)


def parse_page(html: str) -> tuple[dict, BeautifulSoup]:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = ""
    if meta_desc_tag and meta_desc_tag.get("content"):
        meta_description = meta_desc_tag["content"].strip()

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append({"level": tag.name, "text": text})

    first_image = ""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        first_image = og_image["content"].strip()
    else:
        first_img_tag = soup.find("img", src=True)
        if first_img_tag:
            first_image = first_img_tag["src"].strip()

    page_data = {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "first_image": first_image,
    }
    return page_data, soup


class HTTPError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
