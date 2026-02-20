import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import psycopg
import requests
import yaml

from scrape.plone import (
    discover_plone_news_events,
    discover_plone_security,
    extract_plone_article,
)


DROP_PARAMS_PREFIX = ("utm_",)
DROP_PARAMS_EXACT = {"ref", "source", "feature"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def canonicalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return u
    p = urlsplit(u)
    p = p._replace(fragment="")
    q = []
    for k, v in parse_qsl(p.query, keep_blank_values=True):
        if k.startswith(DROP_PARAMS_PREFIX):
            continue
        if k in DROP_PARAMS_EXACT:
            continue
        q.append((k, v))
    p = p._replace(query=urlencode(q, doseq=True))
    path = p.path.rstrip("/") or "/"
    p = p._replace(path=path)
    return urlunsplit(p)


def load_sources_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_topic_sources(cfg: Dict[str, Any], topic: str) -> List[Dict[str, Any]]:
    topic_cfg = cfg.get("topics", {}).get(topic, {})
    return [s for s in (topic_cfg.get("sources", []) or []) if s.get("enabled", True)]


def upsert_sources(conn: psycopg.Connection, topic: str, sources: List[Dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        for s in sources:
            cur.execute(
                """
                INSERT INTO sources (id, topic, source_type, name, url, enabled, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  topic = EXCLUDED.topic,
                  source_type = EXCLUDED.source_type,
                  name = EXCLUDED.name,
                  url = EXCLUDED.url,
                  enabled = EXCLUDED.enabled,
                  updated_at = now()
                """,
                (s["id"], topic, s["type"], s.get("name"), s["url"], bool(s.get("enabled", True))),
            )


def load_scrape_sources_from_db(conn: psycopg.Connection, topic: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, url, name, last_published_at
            FROM sources
            WHERE topic=%s AND source_type='scrape' AND enabled=true
            ORDER BY id
            """,
            (topic,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def update_source_fetched(conn: psycopg.Connection, source_id: str) -> None:
    """
    Para scrapes sin fecha fiable: NO tocar last_published_at.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET last_fetched_at=now(),
                updated_at=now()
            WHERE id=%s
            """,
            (source_id,),
        )


def insert_item(
    conn: psycopg.Connection,
    topic: str,
    source_id: str,
    title: str,
    url: str,
    canonical_url: str,
    published_at: datetime,
    fetched_at: datetime,
    content_text: str,
    tags: Optional[List[str]],
    raw: Dict[str, Any],
) -> bool:
    content_text = (content_text or "").strip()
    content_hash = sha256_text(content_text) if content_text else None

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO items
              (topic, source_id, source_type, title, url, canonical_url,
               published_at, fetched_at, content_text, content_hash,
               status, priority, tags, raw)
            VALUES
              (%s, %s, 'scrape', %s, %s, %s,
               %s, %s, %s, %s,
               'new', 0, %s, %s::jsonb)
            ON CONFLICT (topic, canonical_url) DO NOTHING            """,
            (
                topic,
                source_id,
                title,
                url,
                canonical_url,
                published_at,
                fetched_at,
                content_text if content_text else None,
                content_hash,
                tags if tags else None,
                json.dumps(raw, ensure_ascii=False, default=str),
            ),
        )
        return cur.rowcount == 1


def fetch(url: str, timeout: int = 20, user_agent: str = "TechWatchBot/1.0") -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    r.raise_for_status()
    return r.text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, choices=["plone", "django", "ai"])
    ap.add_argument("--sources", default=os.environ.get("SOURCES_YAML", "sources.yaml"))
    ap.add_argument("--db", default=os.environ.get("DATABASE_URL"))
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("DATABASE_URL not set. Provide --db or set env DATABASE_URL.")

    cfg = load_sources_yaml(args.sources)
    yaml_sources = iter_topic_sources(cfg, args.topic)

    with psycopg.connect(args.db) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.commit()

        upsert_sources(conn, args.topic, yaml_sources)
        conn.commit()

        scrape_sources = load_scrape_sources_from_db(conn, args.topic)
        if not scrape_sources:
            print("No scrape sources enabled.")
            return

        tags_by_id = {s["id"]: s.get("tags") for s in yaml_sources if s.get("type") == "scrape"}
        parser_by_id = {s["id"]: s.get("parser") for s in yaml_sources if s.get("type") == "scrape"}

        inserted_total = 0

        for src in scrape_sources:
            source_id = src["id"]
            base_url = src["url"]
            parser = parser_by_id.get(source_id)
            tags = tags_by_id.get(source_id)

            print(f"\n--- Scraping {source_id}: {base_url} (parser={parser})")

            listing_html = fetch(base_url)
            if parser == "plone_news_events":
                links = discover_plone_news_events(listing_html, base_url)
            elif parser == "plone_security":
                links = discover_plone_security(listing_html, base_url)
            else:
                print(f"  ❌ unknown parser '{parser}' for source '{source_id}'")
                continue

            print(f"  discovered links: {len(links)}")

            inserted = 0

            for link in links[:100]:  # cap
                article_url = link.url
                canonical = canonicalize_url(article_url)

                fetched_at = utcnow()
                html = fetch(article_url)
                title, published_at_real, text = extract_plone_article(html, article_url)

                # Si NO hay published_at real, usa fetched_at para poder hacer ventana semanal.
                inferred = published_at_real is None
                published_at = published_at_real or fetched_at

                raw = {
                    "listing_url": base_url,
                    "article_url": article_url,
                    "html": html,
                    "parser": parser,
                    "published_at_inferred": inferred,
                    "published_at_real": published_at_real.isoformat() if published_at_real else None,
                }

                ok = insert_item(
                    conn,
                    topic=args.topic,
                    source_id=source_id,
                    title=title,
                    url=article_url,
                    canonical_url=canonical,
                    published_at=published_at,
                    fetched_at=fetched_at,
                    content_text=text,
                    tags=tags,
                    raw=raw,
                )
                if ok:
                    inserted += 1
                    inserted_total += 1

            update_source_fetched(conn, source_id)
            conn.commit()

            print(f"  inserted: {inserted} | note: published_at may be inferred from fetched_at")

        print("\nDone.")
        print(f"Inserted new items: {inserted_total}")


if __name__ == "__main__":
    main()
