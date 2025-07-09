import logging
import re
import time
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

def is_google_news_url(url: str) -> bool:
    return "news.google.com" in urlparse(url).netloc

def looks_like_article_url(href: str) -> bool:
    return href and href.startswith("http") and not is_google_news_url(href)

@app.route("/")
def index():
    return "Redirect Resolver API is running"

@app.route("/resolve")
def resolve():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    logger.info("[Resolver] 🟡 Starting resolution: %s", url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            logger.info("[Resolver] Navigating to initial URL (domcontentloaded, 60s timeout)...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")

            start_time = time.time()
            current_url = page.url

            # Step 1: Try JS-based redirect by polling for URL change
            for i in range(15):
                current_url = page.url
                logger.debug("[Resolver] Poll step %d: current URL = %s", i + 1, current_url)
                if not is_google_news_url(current_url):
                    logger.info("[Resolver] ✅ JS-based redirect successful after %d seconds", i + 1)
                    break
                page.wait_for_timeout(1000)
            else:
                logger.warning("[Resolver] JS redirect not detected after 15s. Trying fallback strategies...")

                # Fallback 1: Check meta refresh tag
                meta = page.query_selector('meta[http-equiv="refresh"]')
                if meta:
                    content = meta.get_attribute("content")
                    logger.info("[Resolver] Found meta refresh content: %s", content)
                    if content:
                        match = re.search(r'url=(.+)', content, re.IGNORECASE)
                        if match:
                            redirect_url = match.group(1).strip()
                            logger.info("[Resolver] 🔁 Navigating to meta refresh URL: %s", redirect_url)
                            page.goto(redirect_url, timeout=60000, wait_until="domcontentloaded")
                            page.wait_for_timeout(5000)
                            current_url = page.url
                            logger.info("[Resolver] ✅ Meta refresh resolved to: %s", current_url)
                        else:
                            logger.warning("[Resolver] Meta tag found but no valid URL detected")
                    else:
                        logger.warning("[Resolver] Meta tag had no content attribute")
                else:
                    logger.info("[Resolver] No meta refresh tag found")

                # Fallback 2: Anchor-based redirect
                if is_google_news_url(current_url):
                    anchors = page.query_selector_all("a[href]")
                    found = False
                    for anchor in anchors:
                        href = anchor.get_attribute("href")
                        if looks_like_article_url(href):
                            logger.info("[Resolver] 🔁 Navigating to anchor fallback link: %s", href)
                            page.goto(href, timeout=60000, wait_until="domcontentloaded")
                            page.wait_for_timeout(5000)
                            current_url = page.url
                            logger.info("[Resolver] ✅ Anchor fallback resolved to: %s", current_url)
                            found = True
                            break
                    if not found:
                        logger.warning("[Resolver] No usable anchor links found")

            browser.close()

        elapsed = time.time() - start_time

        if is_google_news_url(current_url):
            logger.error("[Resolver] ❌ Resolution failed — still on Google News after %.2f seconds. Original URL: %s", elapsed, url)
            return jsonify({
                "error": "Could not resolve final destination — still a Google News URL",
                "intermediate_url": current_url
            }), 400

        logger.info("[Resolver] ✅ SUCCESS after %.2f seconds. Final URL: %s", elapsed, current_url)
        return jsonify({"resolved_url": current_url})

    except PlaywrightTimeoutError:
        logger.exception("[Resolver] ⏱ Timeout error while loading. Original URL: %s", url)
        return jsonify({"error": "Timeout while loading the page"}), 504

    except Exception as e:
        logger.exception("[Resolver] 💥 Unexpected error. Original URL: %s", url)
        return jsonify({
            "error": "Failed to resolve redirect",
            "detail": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
