import os
import time
import logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def index():
    return "Redirect Resolver API is running"

@app.route("/resolve")
def resolve():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    logger.info("[Resolver] Navigating to: %s", url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            resolved_url = page.url
            browser.close()

        parsed = urlparse(resolved_url)
        if not parsed.scheme.startswith("http"):
            raise ValueError("Invalid scheme in resolved URL")

        logger.info("[Resolver] Final resolved URL: %s", resolved_url)
        return jsonify({"resolved_url": resolved_url})

    except Exception as e:
        logger.exception("[Resolver] Exception: %s", str(e))
        return jsonify({"error": "Failed to resolve redirect", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
