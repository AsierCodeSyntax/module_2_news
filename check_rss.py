import feedparser
import requests
from pprint import pprint

RSS_FEEDS = {
   "django fundation" : "https://www.djangoproject.com/rss/foundation/",
}

def check_feed(name, url):
    print(f"\n🔍 Checking: {name}")
    print(f"URL: {url}")

    # Definimos cabeceras de un navegador real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        # Primero descargamos el contenido con requests
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Lanza error si hay bloqueo (403, 404, etc)
        
        # Luego se lo pasamos a feedparser desde el contenido ya descargado
        feed = feedparser.parse(response.content)

        if not feed.entries:
            print("⚠️ Parsed but no entries found (Possible empty feed)")
            return

        print(f"✅ VALID RSS")
        print(f"Entries found: {len(feed.entries)}")
        first = feed.entries[0]
        print(f"  - title: {first.get('title')}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    for name, url in RSS_FEEDS.items():
        check_feed(name, url)
