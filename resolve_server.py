import re
import time
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route("/resolve", methods=["GET"])
def resolve_redirect():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print(f"[Resolver] Attempting to resolve: {url}")

            # ✅ Use less strict waiting to reduce timeout errors
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            time.sleep(2)  # brief pause for redirects/meta-refresh
            content = page.content()
            print("[Resolver] Page content preview:")
            print(content[:1000])

            # Try to extract canonical or final link
            resolved_url = page.url
            print(f"[Resolver] Final resolved URL: {resolved_url}")

            browser.close()

            return jsonify({"resolved_url": resolved_url})
    except Exception as e:
        print(f"[Resolver] Exception: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def index():
    return "Redirect Resolver API is running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
