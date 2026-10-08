#!/usr/bin/env python3
"""Manko RSS feed builder -- 图片优先的 RSS 2.0 订阅源.

输入: items.json -- 条目列表, 每项字段:
    code    番号, 如 "092826_01"
    title   标题 (多数条目只有番号, 可空)
    url     详情页 URL, 如 "https://manko.fun/movie-info/<id>?series=false"
    image   封面图 URL (image.healertanker.com CDN, 已验证可直连)
    date    发布日期 YYYY-MM-DD
    score   评分 (imdb_score, 0-10, 可空/0)

输出:
    manko-feed.xml -- RSS 2.0 + Media RSS, 图片通过三种方式突出:
        1. <media:thumbnail>/<media:content> (Feedly/Inoreader 等识别展示大图)
        2. <enclosure> 图片附件 (部分阅读器展示)
        3. <description> 内嵌大图 <img> (所有阅读器兜底)
    preview.html -- 图片优先的订阅预览页 (大图卡片网格)
"""
import json
import html
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parent
ITEMS_JSON = BASE / "items.json"
FEED_XML = BASE / "manko-feed.xml"
PREVIEW_HTML = BASE / "preview.html"

FEED_TITLE = "Manko 热门速递"
FEED_LINK = "https://manko.fun/home"
FEED_DESC = "Manko 首页 Popular 版块最新影片 -- 封面图优先展示"
FEED_SELF = "https://starmyue.github.io/manko-feed/manko-feed.xml"


def rfc2822(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def fmt_score(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    return f


def qattr(s):
    return escape(s, {'"': "&quot;"})


def full_title_of(it):
    code = it.get("code", "")
    title = (it.get("title") or "").strip()
    if title and title not in code and code not in title:
        return "【" + code + "】" + title
    return code


def build_description(item):
    """description 内嵌大图: 图片永远在最前面、最显眼."""
    parts = []
    img = item.get("image", "")
    if img:
        parts.append(
            '<p style="margin:0 0 12px 0;text-align:center;">'
            + '<a href="' + qattr(item.get("url", "")) + '">'
            + '<img src="' + qattr(img) + '" '
            + 'style="max-width:100%;height:auto;border-radius:8px;" '
            + 'alt="' + escape(item.get("code", "")) + '"/>'
            + "</a></p>"
        )
    meta = []
    if item.get("date"):
        meta.append("日期: " + html.escape(item["date"]))
    score = fmt_score(item.get("score"))
    if score:
        meta.append("评分: %.2f/10" % score)
    if meta:
        parts.append("<p>" + " · ".join(meta) + "</p>")
    title = (item.get("title") or "").strip()
    code = item.get("code", "")
    if title and title not in code and code not in title:
        parts.append("<p>" + html.escape(title) + "</p>")
    return "".join(parts)


def build_xml(items, note):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append('<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" '
             'xmlns:atom="http://www.w3.org/2005/Atom">')
    L.append("  <channel>")
    L.append("    <title>" + escape(FEED_TITLE) + "</title>")
    L.append("    <link>" + FEED_LINK + "</link>")
    L.append("    <description>" + escape(FEED_DESC) + "</description>")
    L.append("    <language>zh-cn</language>")
    L.append("    <lastBuildDate>" + now + "</lastBuildDate>")
    L.append('    <atom:link href="' + FEED_SELF + '" rel="self" type="application/rss+xml"/>')
    L.append("    <!-- " + escape(note) + " -->")
    for it in items:
        img = it.get("image", "")
        L.append("    <item>")
        L.append("      <title>" + escape(full_title_of(it)) + "</title>")
        L.append("      <link>" + escape(it.get("url", "")) + "</link>")
        L.append('      <guid isPermaLink="true">' + escape(it.get("url", "")) + "</guid>")
        L.append("      <pubDate>" + rfc2822(it.get("date", "")) + "</pubDate>")
        if img:
            L.append('      <media:thumbnail url="' + qattr(img) + '"/>')
            L.append('      <media:content url="' + qattr(img) + '" type="image/jpeg" '
                     'medium="image"/>')
            L.append('      <enclosure url="' + qattr(img) + '" type="image/jpeg"/>')
        L.append("      <description><![CDATA[" + build_description(it) + "]]></description>")
        L.append("    </item>")
    L.append("  </channel>")
    L.append("</rss>")
    return "\n".join(L) + "\n"


CARD_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#14161c;color:#e8eaf0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:24px 16px}
header{max-width:1200px;margin:0 auto 20px}
header h1{font-size:22px;margin-bottom:6px}
header p{color:#9aa0b0;font-size:13px}
.grid{max-width:1200px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{background:#1d2029;border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;display:block;transition:transform .15s}
.card:hover{transform:translateY(-3px)}
.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#0c0e12}
.card .body{padding:12px 14px 14px}
.card .code{font-size:13px;color:#7fd4ff;letter-spacing:.5px;margin-bottom:6px;font-weight:600}
.card .meta{font-size:12px;color:#9aa0b0;line-height:1.7}
footer{max-width:1200px;margin:28px auto 0;color:#6b7280;font-size:12px;text-align:center}
"""


def build_html(items, note):
    cards = []
    for it in items:
        img = it.get("image", "")
        meta = []
        if it.get("date"):
            meta.append(html.escape(it["date"]))
        score = fmt_score(it.get("score"))
        if score:
            meta.append("★ %.2f" % score)
        meta_html = '<div class="meta">' + " · ".join(meta) + "</div>" if meta else ""
        cards.append(
            '<a class="card" href="' + qattr(it.get("url", "")) + '" target="_blank" rel="noopener">'
            '<img loading="lazy" src="' + qattr(img) + '" alt="' + escape(it.get("code", "")) + '"/>'
            '<div class="body">'
            '<div class="code">' + escape(it.get("code", "")) + "</div>"
            + meta_html + "</div></a>"
        )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="UTF-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        "<title>" + html.escape(FEED_TITLE) + " -- 图片订阅预览</title>\n"
        "<style>" + CARD_CSS + "</style>\n</head>\n<body>\n<header>\n<h1>📡 "
        + html.escape(FEED_TITLE) + "</h1>\n<p>" + html.escape(note) + "</p>\n</header>\n"
        '<div class="grid">\n' + "".join(cards) + "\n</div>\n"
        "<footer>共 " + str(len(items)) + " 条 · 点击卡片打开原站详情页</footer>\n"
        "</body>\n</html>\n"
    )


def main():
    if not ITEMS_JSON.exists():
        print("缺少 %s, 先运行 refresh.py 抓取数据" % ITEMS_JSON, file=sys.stderr)
        sys.exit(1)
    items = json.loads(ITEMS_JSON.read_text(encoding="utf-8"))
    note = "共 %d 条, 生成于 %s UTC" % (len(items), datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    FEED_XML.write_text(build_xml(items, note), encoding="utf-8")
    PREVIEW_HTML.write_text(build_html(items, note), encoding="utf-8")
    print("OK: %d items -> %s, %s" % (len(items), FEED_XML.name, PREVIEW_HTML.name))


if __name__ == "__main__":
    main()
