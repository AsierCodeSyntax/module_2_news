import re
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any
from urllib.parse import urljoin

import bs4  # beautifulsoup4


@dataclass
class DiscoveredLink:
    url: str
    title: Optional[str] = None
    published_at: Optional[datetime] = None


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _try_parse_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None

    # ISO8601 (y variantes con Z)
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # "YYYY-MM-DD" simple
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    return None


def _extract_from_jsonld(soup: bs4.BeautifulSoup) -> Optional[datetime]:
    """
    Busca datePublished/dateModified en JSON-LD.
    Plone suele incluir schema.org JSON-LD en muchas páginas.
    """
    scripts = soup.select('script[type="application/ld+json"]')
    for sc in scripts:
        raw = sc.string or sc.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        dt = _find_date_in_jsonld(data)
        if dt:
            return dt

    return None


def _find_date_in_jsonld(data: Any) -> Optional[datetime]:
    """
    data puede ser dict o list. Buscamos datePublished / dateModified recursivo.
    """
    if isinstance(data, list):
        for x in data:
            dt = _find_date_in_jsonld(x)
            if dt:
                return dt
        return None

    if isinstance(data, dict):
        for k in ("datePublished", "dateModified", "dateCreated"):
            if k in data and isinstance(data[k], str):
                dt = _try_parse_dt(data[k])
                if dt:
                    return dt

        # a veces viene dentro de "@graph"
        if "@graph" in data:
            return _find_date_in_jsonld(data["@graph"])

        # recursivo sobre valores
        for v in data.values():
            if isinstance(v, (dict, list)):
                dt = _find_date_in_jsonld(v)
                if dt:
                    return dt

    return None


def _extract_from_meta(soup: bs4.BeautifulSoup) -> Optional[datetime]:
    """
    Metas frecuentes en CMS:
    - article:published_time / article:modified_time
    - DC.date / DC.created
    - og:updated_time
    """
    selectors = [
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
    for sel in selectors:
        meta = soup.select_one(sel)
        if meta:
            dt = _try_parse_dt(meta.get("content", ""))
            if dt:
                return dt
    return None


def _extract_from_time_tag(soup: bs4.BeautifulSoup) -> Optional[datetime]:
    time_el = soup.select_one("time[datetime]")
    if time_el:
        dt = _try_parse_dt(time_el.get("datetime", ""))
        if dt:
            return dt
    return None


def _extract_from_visible_text(soup: bs4.BeautifulSoup) -> Optional[datetime]:
    """
    Último fallback: busca una fecha en el texto visible.
    Útil si Plone muestra "Effective date: 2024-..." o similar.
    """
    container = soup.select_one("main") or soup.select_one("article") or soup.body
    if not container:
        return None

    for bad in container.select("script, style, noscript"):
        bad.decompose()

    txt = _clean_text(container.get_text(" ", strip=True))

    # ISO date visible
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", txt)
    if m:
        return _try_parse_dt(m.group(0))

    # También intenta “Month DD, YYYY” en inglés (muy común)
    m2 = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b",
        txt,
    )
    if m2:
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
            "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
        }
        try:
            dt = datetime(int(m2.group(3)), month_map[m2.group(1)], int(m2.group(2)), tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    return None


def _extract_published_at(soup: bs4.BeautifulSoup) -> Optional[datetime]:
    # orden: lo más fiable primero
    return (
        _extract_from_time_tag(soup)
        or _extract_from_meta(soup)
        or _extract_from_jsonld(soup)
        or _extract_from_visible_text(soup)
    )


def discover_plone_news_events(listing_html: str, base_url: str) -> List[DiscoveredLink]:
    soup = bs4.BeautifulSoup(listing_html, "html.parser")
    out: List[DiscoveredLink] = []

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        if "plone.org" not in abs_url:
            continue

        # links bajo news-and-events (evita la propia listing)
        if "/news-and-events" in abs_url and abs_url.rstrip("/") != base_url.rstrip("/"):
            title = _clean_text(a.get_text(" ", strip=True))
            out.append(DiscoveredLink(url=abs_url, title=title if title else None))

    # dedupe
    seen = set()
    uniq = []
    for x in out:
        if x.url in seen:
            continue
        seen.add(x.url)
        uniq.append(x)
    return uniq


def discover_plone_security(listing_html: str, base_url: str) -> List[DiscoveredLink]:
    soup = bs4.BeautifulSoup(listing_html, "html.parser")
    out: List[DiscoveredLink] = []

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        if "plone.org" not in abs_url:
            continue

        if "/security" in abs_url and abs_url.rstrip("/") != base_url.rstrip("/"):
            title = _clean_text(a.get_text(" ", strip=True))
            out.append(DiscoveredLink(url=abs_url, title=title if title else None))

    seen = set()
    uniq = []
    for x in out:
        if x.url in seen:
            continue
        seen.add(x.url)
        uniq.append(x)
    return uniq


def extract_plone_article(article_html: str, url: str) -> Tuple[str, Optional[datetime], str]:
    soup = bs4.BeautifulSoup(article_html, "html.parser")

    h1 = soup.select_one("h1")
    if h1:
        title = _clean_text(h1.get_text(" ", strip=True))
    else:
        t = soup.select_one("title")
        title = _clean_text(t.get_text(" ", strip=True)) if t else url

    published_at = _extract_published_at(soup)

    container = soup.select_one("main") or soup.select_one("article") or soup.body
    text = ""
    if container:
        for bad in container.select("script, style, noscript"):
            bad.decompose()
        text = _clean_text(container.get_text(" ", strip=True))

    return title, published_at, text
