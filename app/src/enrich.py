import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

import psycopg


STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","by","from","at","as","is","are","was","were",
    "this","that","these","those","it","its","be","can","may","will","we","you","they","their","our","your",
    "new","release","released","version"
}

SECURITY_RE = re.compile(r"\b(cve-\d{4}-\d+|security|vulnerab|hotfix|patch)\b", re.I)
RELEASE_RE = re.compile(r"\b(release|released|version|tag|changelog)\b", re.I)


def utcnow():
    return datetime.now(timezone.utc)


def tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    words = re.findall(r"[a-z0-9][a-z0-9\.\-_]{2,}", text)
    return [w for w in words if w not in STOPWORDS]


def top_keywords(text: str, k: int = 8) -> List[str]:
    words = tokenize(text)
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:k]]


def compute_priority(topic: str, source_id: str, title: str, content: str, tags: List[str]) -> int:
    """
    Prioridad simple y transparente:
    - Security muy alto
    - Official > community
    - Releases alto
    """
    t = f"{title}\n{content}"

    if SECURITY_RE.search(t) or ("security" in (tags or [])) or ("cve" in (tags or [])):
        return 100

    official = ("official" in (tags or [])) or ("plone.org" in source_id) or ("django_official" in source_id)
    if official:
        base = 60
    else:
        base = 40

    if RELEASE_RE.search(t) or ("release" in (tags or [])):
        base += 15

    return base


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")

    limit = int(os.environ.get("ENRICH_LIMIT", "500"))

    with psycopg.connect(db) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, topic, source_id, title, coalesce(content_text,'') as content_text,
                       coalesce(tags, '{}'::text[]) as tags
                FROM items
                WHERE status='new'
                ORDER BY fetched_at asc
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

        updated = 0
        for (item_id, topic, source_id, title, content_text, tags) in rows:
            kw = top_keywords(f"{title}\n{content_text}", k=8)
            pr = compute_priority(topic, source_id, title, content_text, list(tags))

            # mezcla keywords con tags existentes sin duplicar
            merged_tags = list(dict.fromkeys(list(tags) + kw))

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE items
                    SET priority=%s,
                        tags=%s,
                        status='ready'
                    WHERE id=%s
                    """,
                    (pr, merged_tags, item_id),
                )
            updated += 1

        conn.commit()
        print(f"Enriched items: {updated}")


if __name__ == "__main__":
    main()
