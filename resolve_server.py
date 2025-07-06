from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/resolve", methods=["GET"])
def resolve():
    target_url = request.args.get("url")

    if not target_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    logging.info(f"[Resolver] Attempting to resolve: {target_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, timeout=10000)
            final_url = page.url
            browser.close()

            logging.info(f"[Resolver] Resolved to: {final_url}")
            return jsonify({"resolved_url": final_url})
    except Exception as e:
        logging.error(f"[Resolver] Failed: {e}")
        return jsonify({"error": str(e), "resolved_url": target_url}), 500

@app.route("/", methods=["GET"])
def home():
    return "✅ Link Resolver is running. Use /resolve?url=..."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
