import csv
import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from .slug import title_case_ru, slugify_ru, ensure_unique_slug
from .content_generator import generate_content

def _escape_html(s: str) -> str:
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
             .replace('"',"&quot;").replace("'","&#39;"))

PAGE_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
  <meta name="description" content="{desc}"/>
  <link rel="canonical" href="{canonical}"/>
  <meta property="og:title" content="{title}"/>
  <meta property="og:description" content="{desc}"/>
  <meta property="og:type" content="article"/>
  <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;max-width:820px;margin:32px auto;padding:0 16px;line-height:1.6}}
    .card{{border:1px solid #e7e7e7;border-radius:16px;padding:20px}}
    .btn{{display:inline-block;padding:14px 18px;border-radius:12px;text-decoration:none;background:#111;color:#fff}}
    .muted{{color:#666}}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <p class="muted">{desc}</p>

    {body_html}

    <p><a class="btn" href="{tg_url}" rel="noopener">Перейти в Telegram</a></p>
    <p class="muted">Если Telegram не открылся — нажмите кнопку ещё раз.</p>
  </div>
</body>
</html>
"""

@dataclass
class BuiltItem:
    query: str
    title: str
    slug: str
    url: str
    tg_post: str

def read_queries(csv_path: str) -> List[str]:
    queries: List[str] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "query" not in (reader.fieldnames or []):
            raise ValueError("CSV must have a 'query' column")
        for row in reader:
            q = (row.get("query") or "").strip()
            if q:
                queries.append(q)
    return queries

def build_site_and_posts(
    csv_path: str,
    site_dir: str,
    posts_path: str,
    site_base_url: str,
    tg_group_url: str,
    limit: Optional[int] = None,
) -> List[BuiltItem]:
    os.makedirs(site_dir, exist_ok=True)

    queries = read_queries(csv_path)
    if limit is not None:
        queries = queries[:limit]

    used: Dict[str, int] = {}
    built: List[BuiltItem] = []
    urls_for_sitemap: List[str] = []

    # если posts.jsonl уже есть — не дублируем slug'и
    existing_slugs = set()
    if os.path.exists(posts_path):
        with open(posts_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                s = (obj.get("slug") or "").strip()
                if s:
                    existing_slugs.add(s)
                    used[s] = 1

    with open(posts_path, "a", encoding="utf-8") as pf:
        for q in queries:
            title = title_case_ru(q)
            base_slug = slugify_ru(title)
            slug = ensure_unique_slug(base_slug, used)
            if slug in existing_slugs:
                continue

            url = f"{site_base_url.rstrip('/')}/{slug}/"
            content = generate_content(query=q, title=title, url=url)

            # page
            page_dir = os.path.join(site_dir, slug)
            os.makedirs(page_dir, exist_ok=True)
            html = PAGE_TEMPLATE.format(
                title=_escape_html(title),
                desc=_escape_html(content.description),
                canonical=url,
                body_html=content.page_body_html,
                tg_url=tg_group_url,
            )
            with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as wf:
                wf.write(html)

            record = {
                "query": q,
                "title": title,
                "slug": slug,
                "url": url,
                "tg_post": content.tg_post,
                "description": content.description,
            }
            pf.write(json.dumps(record, ensure_ascii=False) + "\n")
            pf.flush()

            built.append(BuiltItem(query=q, title=title, slug=slug, url=url, tg_post=content.tg_post))
            urls_for_sitemap.append(url)

    write_robots(site_dir, site_base_url)
    write_sitemap(site_dir, urls_for_sitemap)
    write_home_index(site_dir, site_base_url)

    return built

def write_robots(site_dir: str, site_base_url: str) -> None:
    txt = f"""User-agent: *
Allow: /
Sitemap: {site_base_url.rstrip('/')}/sitemap.xml
"""
    with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(txt)

def write_sitemap(site_dir: str, urls: List[str]) -> None:
    today = date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for u in urls:
        lines += [
            "  <url>",
            f"    <loc>{u}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "  </url>"
        ]
    lines.append("</urlset>")
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def write_home_index(site_dir: str, site_base_url: str) -> None:
    base = site_base_url.rstrip("/")
    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Статьи</title>
  <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;max-width:820px;margin:32px auto;padding:0 16px;line-height:1.6}}
    .card{{border:1px solid #e7e7e7;border-radius:16px;padding:20px}}
    a{{color:#0b57d0;text-decoration:none}}
    a:hover{{text-decoration:underline}}
  </style>
</head>
<body>
  <div class="card">
    <h1>Статьи</h1>
    <p>Если ты пришёл сюда из поиска — открой страницу по ссылке из поста.</p>
    <p>Технические файлы:</p>
    <ul>
      <li><a href="{base}/sitemap.xml">sitemap.xml</a></li>
      <li><a href="{base}/robots.txt">robots.txt</a></li>
    </ul>
  </div>
</body>
</html>"""
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
