import json
import logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/")
def health_check():
    return "Redirect Resolver API is healthy"

@app.route("/resolve")
def resolve():
    target_url = request.args.get("url")
    if not target_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # 🚩 Only support Google News wrapper URLs
    if "news.google.com/rss/articles/" not in target_url:
        return jsonify({"error": "Only Google News wrapper URLs are supported"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logging.info(f"[Resolver] Navigating to: {target_url}")
            page.goto(target_url, timeout=30000, wait_until="networkidle")
            final_url = page.url
            browser.close()

            # If we’re still on a Google News page, resolution failed
            if "news.google.com" in final_url:
                logging.warning("[Resolver] Failed to redirect away from Google News.")
                return jsonify({
                    "error": "Could not resolve article destination from Google News wrapper",
                    "fallback": final_url,
                    "resolved_url": None
                }), 400

            return jsonify({"resolved_url": final_url})

    except PlaywrightTimeoutError:
        return jsonify({"error": "Playwright timeout while resolving", "resolved_url": None}), 504

    except Exception as e:
        logging.exception("[Resolver] Unhandled exception")
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
