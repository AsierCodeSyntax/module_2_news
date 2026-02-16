import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

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
    sections = topic_cfg.get("sections")  

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
    Selecciona items EVALUATED (procesados por el LLM) para el topic.
    Ordena por llm_score (nota de la IA) y luego por priority (tu heurística).
    """
    with conn.cursor() as cur:
        query = """
            SELECT id, topic, source_id, title, url, 
                   published_at, priority, tags, summary_short, llm_score
            FROM items
            WHERE topic=%s
              AND status='evaluated'
              AND published_at >= %s
              AND published_at < %s
        """
        params = [topic, since, until]

        if tag_filter:
            query += " AND %s = ANY(tags)"
            params.append(tag_filter)

        # La clave de tu requisito: Ordenar localmente por nota del LLM
        query += " ORDER BY llm_score DESC, priority DESC, published_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
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
                "title": row["title"],
                "url": row["url"],
                "published_at": iso(row["published_at"]),
                "priority": row["priority"],
                "tags": list(row["tags"] or []),
                "summary_short": row["summary_short"],
                "llm_score": row["llm_score"]
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=os.environ.get("SOURCES_YAML", "sources.yaml"))
    ap.add_argument("--db", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--out", default=os.environ.get("BULLETIN_OUT", "app/build/bulletin.json"))
    ap.add_argument("--until", default=None, help="ISO datetime UTC")
    args = ap.parse_args()

    if not args.db:
        raise SystemExit("DATABASE_URL not set.")

    cfg = load_sources_yaml(args.sources)
    until = utcnow()
    if args.until:
        s = args.until.strip().replace("Z", "+00:00")
        until = datetime.fromisoformat(s)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        until = until.astimezone(timezone.utc)

    ensure_dir(os.path.dirname(args.out))

    # Estructura del JSON que consumirá el PDF en LaTeX
    bulletin_payload = {
        "generated_at": iso(utcnow()),
        "topics": {}
    }

    with psycopg.connect(args.db) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.commit()

        # Automatizamos el paso por las 3 categorías
        for topic in ["plone", "django", "ai"]:
            bcfg = get_topic_bulletin_cfg(cfg, topic)
            since = until - timedelta(days=bcfg["window_days"])
            max_items = int(bcfg["max_items"])

            topic_data = {
                "window_days": bcfg["window_days"],
                "since": iso(since),
                "until": iso(until),
            }

            sections = bcfg.get("sections")
            if sections and isinstance(sections, list) and len(sections) > 0:
                per_section = max(1, max_items // len(sections))
                sec_out = []
                for sec in sections:
                    items = select_items_for_topic(conn, topic, since, until, per_section, tag_filter=sec)
                    sec_out.append({"name": sec, "items": items})
                topic_data["sections"] = sec_out
            else:
                items = select_items_for_topic(conn, topic, since, until, max_items, tag_filter=None)
                topic_data["items"] = items

            bulletin_payload["topics"][topic] = topic_data

        # Actualizamos el estado de las noticias en la BD a 'published' para no repetir en el futuro
        # (Esto es opcional pero muy recomendado para no tener noticias zombie). De momento solo generamos el JSON.
        
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(bulletin_payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Boletín global generado con éxito en: {args.out}")
    for t, d in bulletin_payload["topics"].items():
        if "sections" in d:
            total = sum(len(s["items"]) for s in d["sections"])
            print(f" 📌 {t.upper()}: {total} items seleccionados (divididos en secciones)")
        else:
            print(f" 📌 {t.upper()}: {len(d['items'])} items seleccionados")


if __name__ == "__main__":
    main()