import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psycopg
import yaml


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_sources_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_topic_bulletin_cfg(cfg: Dict[str, Any], topic: str) -> Dict[str, Any]:
    defaults = cfg.get("defaults", {}).get("bulletin", {}) or {}
    topic_cfg = cfg.get("topics", {}).get(topic, {}).get("bulletin", {}) or {}

    window_days = int(topic_cfg.get("window_days", defaults.get("window_days", 7)))
    max_items = int(topic_cfg.get("max_items", 15))

    # opcional: sections para ai
    sections = topic_cfg.get("sections")  # puede ser None

    return {"window_days": window_days, "max_items": max_items, "sections": sections}


def iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def select_items_for_topic(
    conn: psycopg.Connection,
    topic: str,
    since: datetime,
    until: datetime,
    limit: int,
    tag_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Selecciona items READY para el topic.
    Si tag_filter está presente, filtra items que contengan ese tag (p.ej. 'arxiv' o 'industry').
    """
    with conn.cursor() as cur:
        if tag_filter:
            cur.execute(
                """
                SELECT id, topic, source_id, source_type, title, url, canonical_url,
                       published_at, fetched_at, priority, tags
                FROM items
                WHERE topic=%s
                  AND status='ready'
                  AND published_at >= %s
                  AND published_at < %s
                  AND %s = ANY(tags)
                ORDER BY priority DESC, published_at DESC NULLS LAST, fetched_at DESC
                LIMIT %s
                """,
                (topic, since, until, tag_filter, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, topic, source_id, source_type, title, url, canonical_url,
                       published_at, fetched_at, priority, tags
                FROM items
                WHERE topic=%s
                  AND status='ready'
                  AND published_at >= %s
                  AND published_at < %s
                ORDER BY priority DESC, published_at DESC NULLS LAST, fetched_at DESC
                LIMIT %s
                """,
                (topic, since, until, limit),
            )

        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

    out = []
    for r in rows:
        row = dict(zip(cols, r))
        out.append(
            {
                "id": row["id"],
                "topic": row["topic"],
                "source_id": row["source_id"],
                "source_type": row["source_type"],
                "title": row["title"],
                "url": row["url"],
                "canonical_url": row["canonical_url"],
                "published_at": iso(row["published_at"]),
                "fetched_at": iso(row["fetched_at"]),
                "priority": row["priority"],
                "tags": list(row["tags"] or []),
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, choices=["plone", "django", "ai"])
    ap.add_argument("--sources", default=os.environ.get("SOURCES_YAML", "sources.yaml"))
    ap.add_argument("--db", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--out", default=os.environ.get("BULLETIN_OUT", "app/build/bulletin.json"))
    ap.add_argument("--until", default=None, help="ISO datetime UTC (default: now). Example: 2026-02-13T00:00:00Z")
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("DATABASE_URL not set. Provide --db or set env DATABASE_URL.")

    cfg = load_sources_yaml(args.sources)
    bcfg = get_topic_bulletin_cfg(cfg, args.topic)

    until = utcnow()
    if args.until:
        s = args.until.strip().replace("Z", "+00:00")
        until = datetime.fromisoformat(s)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        until = until.astimezone(timezone.utc)

    since = until - timedelta(days=bcfg["window_days"])
    max_items = int(bcfg["max_items"])

    ensure_dir(os.path.dirname(args.out))

    with psycopg.connect(args.db) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.commit()

        # Si topic ai tiene secciones ["industry","arxiv"], hacemos split por tags
        sections = bcfg.get("sections")
        payload: Dict[str, Any] = {
            "generated_at": iso(utcnow()),
            "topic": args.topic,
            "window": {"since": iso(since), "until": iso(until), "window_days": bcfg["window_days"]},
            "max_items": max_items,
        }

        if sections and isinstance(sections, list) and len(sections) > 0:
            per_section = max(1, max_items // len(sections))
            sec_out = []
            for sec in sections:
                items = select_items_for_topic(conn, args.topic, since, until, per_section, tag_filter=sec)
                sec_out.append({"name": sec, "items": items})
            payload["sections"] = sec_out
            payload["items"] = []  # para consistencia
        else:
            items = select_items_for_topic(conn, args.topic, since, until, max_items, tag_filter=None)
            payload["items"] = items

        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {args.out}")
    if payload.get("sections"):
        for sec in payload["sections"]:
            print(f"Section '{sec['name']}': {len(sec['items'])} items")
    else:
        print(f"Items: {len(payload['items'])}")


if __name__ == "__main__":
    main()
