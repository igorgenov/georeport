import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from app.scraper import fetch_page, parse_page, HTTPError
from app.scorer import run_scoring
from app.llm import generate_schema


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON body.")
            return

        url = data.get("url", "").strip()
        api_key = data.get("api_key", "").strip()

        if not url:
            self._send_error(400, "Missing 'url' in request body.")
            return
        if not api_key:
            self._send_error(400, "Missing 'api_key' in request body.")
            return

        try:
            html, final_url = fetch_page(url)
            page_data, soup = parse_page(html)
            scoring_result = run_scoring(soup)
            recommended_schema = generate_schema(page_data, final_url, api_key)

            response = {
                "url": final_url,
                "geo_score": scoring_result["geo_score"],
                "geo_grade": scoring_result["geo_grade"],
                "metrics": scoring_result["metrics"],
                "recommendations": scoring_result["recommendations"],
                "recommended_schema": recommended_schema,
                "page_title": page_data.get("title", ""),
                "page_description": page_data.get("meta_description", ""),
                "page_headings": page_data.get("headings", []),
                "page_image": page_data.get("first_image", ""),
            }

            self._send_json(200, response)

        except HTTPError as e:
            self._send_error(e.status_code, e.detail)
        except Exception as e:
            self._send_error(500, f"Internal error: {str(e)}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self._add_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code: int, detail: str):
        self.send_response(status_code)
        self._add_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": detail}).encode())

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
