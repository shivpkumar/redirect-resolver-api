from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def extract_final_url(html, original_url):
    soup = BeautifulSoup(html, 'html.parser')

    # Try canonical markers
    candidates = [
        soup.find('meta', property='og:url'),
        soup.find('meta', attrs={'name': 'twitter:url'}),
        soup.find('link', rel='canonical')
    ]
    for tag in candidates:
        if tag and tag.get('content'):
            return tag['content']
        if tag and tag.get('href'):
            return tag['href']

    # Fallback: if <meta http-equiv="refresh"> exists, extract from there
    refresh_tag = soup.find('meta', attrs={'http-equiv': 'refresh'})
    if refresh_tag and 'url=' in refresh_tag.get('content', ''):
        return refresh_tag['content'].split('url=')[-1].strip()

    return None

@app.route('/resolve')
def resolve():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()

        # 1. Try meta tags from final response
        final_url = extract_final_url(resp.text, url)

        # 2. Fallback: Use requests' final URL after redirects
        if not final_url or "news.google.com" in final_url:
            final_url = resp.url

        # Still unresolved? Return error
        if "news.google.com" in final_url:
            return jsonify({
                'error': 'Could not resolve article destination from Google News wrapper',
                'resolved_url': None,
                'fallback': resp.url
            }), 502

        return jsonify({'resolved_url': final_url})

    except Exception as e:
        return jsonify({'error': str(e), 'resolved_url': None}), 500

@app.route('/')
def home():
    return 'Google News Redirect Resolver is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
