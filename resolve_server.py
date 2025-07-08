from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def extract_final_url(html, original_url):
    soup = BeautifulSoup(html, 'html.parser')

    # Check common canonical markers
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

    return None  # fallback will be handled by caller

@app.route('/resolve')
def resolve():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        final_url = extract_final_url(resp.text, url)
        if final_url:
            return jsonify({'resolved_url': final_url})
        else:
            return jsonify({
                'error': 'Could not extract resolved URL from HTML',
                'resolved_url': None,
                'fallback': url
            }), 502

    except Exception as e:
        return jsonify({'error': str(e), 'resolved_url': None}), 500

@app.route('/')
def home():
    return 'Google News Redirect Resolver is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
