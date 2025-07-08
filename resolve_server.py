import logging
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
import asyncio

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/resolve")
def resolve():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        resolved_url = asyncio.run(resolve_with_browser(url))
        if resolved_url:
            return jsonify({"resolved_url": resolved_url})
        else:
            return jsonify({"error": "Could not resolve URL"}), 400
    except Exception as e:
        logging.exception(f"[Resolver] Exception during resolution: {e}")
        return jsonify({"error": "Server error"}), 500

async def resolve_with_browser(url: str) -> str:
    logging.info(f"[Resolver] Attempting to resolve: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="networkidle")
        except Exception as e:
            logging.warning(f"[Resolver] Timeout or navigation error: {e}")
            await browser.close()
            return None

        try:
            final_url = page.url
            logging.info(f"[Resolver] Final resolved URL: {final_url}")
            return final_url
        except Exception as e:
            logging.error(f"[Resolver] Could not extract final URL: {e}")
            return None
        finally:
            await browser.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
