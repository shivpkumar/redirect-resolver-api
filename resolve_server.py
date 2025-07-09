import logging
import re
import time
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
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

    logger.info("[Resolver] Resolving: %s", url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            logger.info("[Resolver] Navigating to URL...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Wait up to 15 seconds for a JS redirect to complete
            for i in range(15):
                current_url = page.url
                if not is_google_news_url(current_url):
                    logger.info("[Resolver] Redirected to: %s", current_url)
                    break
                logger.info("[Resolver] Still on Google News after %d sec...", i + 1)
                page.wait_for_timeout(1000)  # 1 second
            else:
                logger.warning("[Resolver] Still on Google News after wait. Trying page content...")

                # Try to extract redirect target manually from page content
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Check for meta refresh tag
                meta = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
                if meta and "content" in meta.attrs:
                    match = re.search(r'url=(.+)', meta["content"], re.IGNORECASE)
                    if match:
                        redirect_url = match.group(1).strip()
                        logger.info("[Resolver] Found meta refresh URL: %s", redirect_url)
                        page.goto(redirect_url, timeout=60000, wait_until="domcontentloaded")
                        page.wait_for_timeout(5000)
                        current_url = page.url

                # If still unresolved, try first external link on page
                if is_google_news_url(current_url):
                    links = soup.find_all("a", href=True)
                    for link in links:
                        if looks_like_article_url(link["href"]):
                            redirect_url = link["href"]
                            logger.info("[Resolver] Found external anchor link: %s", redirect_url)
                            page.goto(redirect_url, timeout=60000, wait_until="domcontentloaded")
                            page.wait_for_timeout(5000)
                            current_url = page.url
                            break

            browser.close()

        if is_google_news_url(current_url):
            logger.error("[Resolver] Failed to resolve final destination after all attempts")
            return jsonify({
                "error": "Could not resolve final destination — still a Google News URL",
                "intermediate_url": current_url
            }), 400

        logger.info("[Resolver] Successfully resolved to: %s", current_url)
        return jsonify({"resolved_url": current_url})

    except PlaywrightTimeoutError:
        logger.exception("[Resolver] Playwright timeout error")
        return jsonify({"error": "Timeout while loading the page"}), 504

    except Exception as e:
        logger.exception("[Resolver] Unexpected exception")
        return jsonify({
            "error": "Failed to resolve redirect",
            "detail": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
