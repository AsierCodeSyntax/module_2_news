import argparse
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional

from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import feedparser
import psycopg
import yaml


SAFETY_WINDOW = timedelta(days=3)
DROP_PARAMS_PREFIX = ("utm_",)
DROP_PARAMS_EXACT = {"ref", "source", "feature"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def is_mapping_like(obj: Any) -> bool:
    # FeedParserDict tiene .get/.keys pero no siempre es dict
    return hasattr(obj, "get") and hasattr(obj, "keys")


def mget(obj: Any, key: str, default: Any = None) -> Any:
    if is_mapping_like(obj):
        try:
            return obj.get(key, default)
        except Exception:
            return default
    return getattr(obj, key, default)


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

    path = p.path.rstrip("/")
    if not path:
        path = "/"
    p = p._replace(path=path)

    return urlunsplit(p)


def to_jsonable(obj: Any) -> Any:
    if is_mapping_like(obj):
        try:
            return {str(k): to_jsonable(obj.get(k)) for k in obj.keys()}
        except Exception:
            pass

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]

    return obj


def safe_get_entry_url(entry: Any) -> Optional[str]:
    url = mget(entry, "link")
    if url:
        return str(url).strip()

    links = mget(entry, "links")
    if links and isinstance(links, list):
        first = links[0]
        href = mget(first, "href")
        if href:
            return str(href).strip()

    return None


def safe_get_entry_title(entry: Any) -> str:
    title = mget(entry, "title")
    return (str(title).strip() if title else "").strip() or "(no title)"


def safe_get_entry_published(entry: Any) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        parsed = mget(entry, key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def extract_best_text(entry: Any) -> str:
    content = mget(entry, "content")
    if content and isinstance(content, list) and content:
        val = mget(content[0], "value")
        if val:
            return str(val)

    for k in ("summary", "description"):
        val = mget(entry, k)
        if val:
            return str(val)

    return ""


def load_sources_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_topic_sources(cfg: Dict[str, Any], topic: str) -> Iterable[Dict[str, Any]]:
    topics = cfg.get("topics", {})
    topic_cfg = topics.get(topic, {})
    for src in topic_cfg.get("sources", []) or []:
        if src.get("enabled", True):
            yield src


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
                (
                    s["id"],
                    topic,
                    s["type"],
                    s.get("name"),
                    s["url"],
                    bool(s.get("enabled", True)),
                ),
            )


def load_rss_sources_from_db(conn: psycopg.Connection, topic: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, topic, source_type, name, url, enabled, last_published_at, etag, last_modified
            FROM sources
            WHERE topic=%s AND source_type='rss' AND enabled=true
            ORDER BY id
            """,
            (topic,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def update_source_fetch_only(conn: psycopg.Connection, source_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET last_fetched_at = now(),
                updated_at = now()
            WHERE id = %s
            """,
            (source_id,),
        )


def update_source_state(
    conn: psycopg.Connection,
    source_id: str,
    last_published_at: Optional[datetime],
    etag: Optional[str],
    last_modified: Optional[str],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET last_published_at = %s,
                last_fetched_at = now(),
                etag = %s,
                last_modified = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (last_published_at, etag, last_modified, source_id),
        )


def insert_item(
    conn: psycopg.Connection,
    topic: str,
    source_id: str,
    source_type: str,
    title: str,
    url: str,
    canonical_url: str,
    published_at: Optional[datetime],
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
              (%s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s,
               'new', 0, %s, %s::jsonb)
            ON CONFLICT ON CONSTRAINT uniq_item DO NOTHING            """,
            (
                topic,
                source_id,
                source_type,
                title,
                url,
                canonical_url,
                published_at,
                utcnow(),
                content_text if content_text else None,
                content_hash,
                tags if tags else None,
                json.dumps(raw, ensure_ascii=False, default=str),
            ),
        )
        return cur.rowcount == 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, choices=["plone", "django", "ai"])
    ap.add_argument("--sources", default=os.environ.get("SOURCES_YAML", "sources.yaml"))
    ap.add_argument("--db", default=os.environ.get("DATABASE_URL"))
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("DATABASE_URL not set. Provide --db or set env DATABASE_URL.")

    cfg = load_sources_yaml(args.sources)

    yaml_sources = list(iter_topic_sources(cfg, args.topic))
    if not yaml_sources:
        print(f"No sources found for topic='{args.topic}' in sources.yaml")
        return

    print(f"Topic: {args.topic}")
    print(f"YAML sources: {len(yaml_sources)}")
    print("Connecting to Postgres...")

    with psycopg.connect(args.db) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.commit()

        upsert_sources(conn, args.topic, yaml_sources)
        conn.commit()

        rss_sources = load_rss_sources_from_db(conn, args.topic)
        if not rss_sources:
            print(f"No RSS sources enabled for topic='{args.topic}'")
            return

        print(f"RSS sources enabled: {len(rss_sources)}")

        inserted_total = 0
        seen_total = 0

        max_items = (
            cfg.get("topics", {})
            .get(args.topic, {})
            .get("ingest", {})
            .get("max_items_per_source")
            or cfg.get("defaults", {})
            .get("ingest", {})
            .get("max_items_per_source")
            or 50
        )

        tags_by_id = {s["id"]: s.get("tags") for s in yaml_sources if s.get("type") == "rss"}

        for src in rss_sources:
            source_id = src["id"]
            url = src["url"]
            tags = tags_by_id.get(source_id)

            last_pub = src.get("last_published_at")
            threshold = (last_pub - SAFETY_WINDOW) if last_pub else None

            headers = {}
            if src.get("etag"):
                headers["If-None-Match"] = src["etag"]
            if src.get("last_modified"):
                headers["If-Modified-Since"] = src["last_modified"]

            print(f"\n--- Fetching {source_id}: {url}")
            feed = feedparser.parse(url, request_headers=headers)

            if getattr(feed, "status", None) == 304:
                print("  304 Not Modified (skip)")
                update_source_fetch_only(conn, source_id)
                conn.commit()
                continue

            if getattr(feed, "bozo", False):
                print(f"  ❌ parse error: {getattr(feed, 'bozo_exception', 'unknown')}")
                update_source_fetch_only(conn, source_id)
                conn.commit()
                continue

            entries = getattr(feed, "entries", []) or []
            print(f"  entries: {len(entries)} (processing up to {max_items})")

            inserted = 0
            max_published_seen = last_pub

            for entry in entries[: int(max_items)]:
                seen_total += 1

                entry_url = safe_get_entry_url(entry)
                if not entry_url:
                    continue

                canonical = canonicalize_url(entry_url)
                title = safe_get_entry_title(entry)
                published_at = safe_get_entry_published(entry)

                if threshold and published_at and published_at <= threshold:
                    continue

                text = extract_best_text(entry)

                feed_title = None
                try:
                    feed_title = mget(getattr(feed, "feed", None), "title")
                except Exception:
                    feed_title = None

                raw = {
                    "feed_url": url,
                    "feed_title": feed_title,
                    "entry": to_jsonable(entry),
                }

                ok = insert_item(
                    conn=conn,
                    topic=args.topic,
                    source_id=source_id,
                    source_type="rss",
                    title=title,
                    url=entry_url,
                    canonical_url=canonical,
                    published_at=published_at,
                    content_text=text,
                    tags=tags,
                    raw=raw,
                )

                if ok:
                    inserted += 1
                    inserted_total += 1
                    if published_at:
                        if (max_published_seen is None) or (published_at > max_published_seen):
                            max_published_seen = published_at

            update_source_state(
                conn,
                source_id=source_id,
                last_published_at=max_published_seen,
                etag=getattr(feed, "etag", None),
                last_modified=getattr(feed, "modified", None),
            )
            conn.commit()

            print(f"  inserted: {inserted} | last_published_at: {max_published_seen}")

        print("\nDone.")
        print(f"Seen entries: {seen_total}")
        print(f"Inserted new items: {inserted_total}")


if __name__ == "__main__":
    main()
