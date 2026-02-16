import os
import re
import json
from datetime import datetime, timezone
from typing import Optional

import psycopg
import requests
from bs4 import BeautifulSoup


UA = "TechWatchBot/1.0"


def _try_parse_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def fetch(url: str) -> str:
    r = requests.get(url, timeout=20, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text


def pick_one_url(conn, source_id: str) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select url
            from items
            where source_id=%s
            order by fetched_at desc
            limit 1
            """,
            (source_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def debug_url(url: str) -> None:
    print(f"\n=== DEBUG URL ===\n{url}\n")
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    # time tag
    t = soup.select_one("time[datetime]")
    print("time[datetime]:", t.get("datetime") if t else None)

    # metas
    meta_selectors = [
        'meta[property="article:published_time"][content]',
        'meta[property="article:modified_time"][content]',
        'meta[property="og:updated_time"][content]',
        'meta[name="DC.date"][content]',
        'meta[name="dc.date"][content]',
        'meta[name="DC.created"][content]',
        'meta[name="dc.created"][content]',
        'meta[name="created"][content]',
        'meta[name="modified"][content]',
    ]
    print("\nMETA candidates:")
    for sel in meta_selectors:
        m = soup.select_one(sel)
        if m:
            print(" ", sel, "=>", m.get("content"))

    # JSON-LD
    scripts = soup.select('script[type="application/ld+json"]')
    print(f"\nJSON-LD scripts: {len(scripts)}")
    for i, sc in enumerate(scripts[:3]):
        raw = (sc.string or sc.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                keys = list(data.keys())[:25]
                print(f"  jsonld[{i}] dict keys:", keys)
                for k in ("datePublished", "dateModified", "dateCreated"):
                    if k in data:
                        print(f"    {k}:", data.get(k))
            elif isinstance(data, list):
                print(f"  jsonld[{i}] list len:", len(data))
        except Exception as e:
            print(f"  jsonld[{i}] parse error:", e)

    # URL date pattern
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", url)
    print("\nURL date (YYYY-MM-DD):", m.group(0) if m else None)

    # HTML visible date pattern
    text = soup.get_text(" ", strip=True)
    m2 = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    print("HTML date (YYYY-MM-DD):", m2.group(0) if m2 else None)


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL env not set")

    with psycopg.connect(db) as conn:
        u1 = pick_one_url(conn, "plone_official_news")
        u2 = pick_one_url(conn, "plone_security_advisories")

    if u1:
        debug_url(u1)
    else:
        print("No items found for source plone_official_news")

    if u2:
        debug_url(u2)
    else:
        print("No items found for source plone_security_advisories")


if __name__ == "__main__":
    main()
