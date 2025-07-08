from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import asyncio
from playwright.async_api import async_playwright

app = Flask(__name__)

@app.route("/")
def home():
    return "Redirect Resolver is running!"

@app.route("/resolve", methods=["GET"])
def resolve():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    resolved_url = asyncio.run(resolve_url(url))
    if resolved_url:
        return jsonify({"resolved_url": resolved_url})
    else:
        return jsonify({"error": "Could not resolve URL"}), 500

async def resolve_url(url):
    # Try simple HTML parsing first
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
            if meta_refresh and "url=" in meta_refresh.get("content", ""):
                redirect_url = meta_refresh["content"].split("url=")[-1]
                app.logger.info(f"[HTML Resolver] Resolved via meta-refresh: {redirect_url}")
                return redirect_url
    except Exception as e:
        app.logger.warning(f"[HTML Resolver] Failed: {e}")

    # Fall back to Playwright for JS-based redirects
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=15000)
            final_url = page.url
            await browser.close()
            app.logger.info(f"[Playwright Resolver] Resolved final URL: {final_url}")
            return final_url
    except Exception as e:
        app.logger.error(f"[Playwright Resolver] Failed: {e}")
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
