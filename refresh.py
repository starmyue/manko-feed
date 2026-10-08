#!/usr/bin/env python3
"""Manko 数据刷新脚本: 从站点 API 拉取首页 Popular 最新条目, 重写 items.json 并重新生成 feed.

用法: python3 refresh.py [页数, 默认 3]
原理见 网站分析.md: API 基地址藏在首页 HTML 的 window.ip 中,
路径为 swx/movie/search, 响应 data 字段经站内 xn() 函数 (base91 变体) 加密.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

ALPHABET = ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            '!#$%&()*+,./:;<=>?@[]^_`{|}~"')


def xn_decode(e):
    """JS bundle 中 xn() 解密函数的 Python 移植 (base91 变体 -> UTF-8 JSON)."""
    t = str(e or "")
    r = bytearray()
    a = 0
    i = 0
    o = -1
    for ch in t:
        l = ALPHABET.find(ch)
        if l == -1:
            continue
        if o < 0:
            o = l
        else:
            o = o + 91 * l
            a |= o << i
            i += 13 if (8191 & o) > 88 else 14
            while i > 7:
                r.append(255 & a)
                a >>= 8
                i -= 8
            o = -1
    if o > -1:
        r.append(255 & (a | (o << i)))
    return bytes(r).decode("utf-8")


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def discover_api_base():
    """从首页 HTML 解析 window.ip (API 域名, 另有 window.ip2 为备用)."""
    html = http_get("https://manko.fun/home")
    m = re.search(r"""\bip\s*=\s*['"]([a-zA-Z0-9.\-]{4,60})['"]""", html)
    if not m:
        raise RuntimeError("首页 HTML 中未找到 window.ip")
    return m.group(1)


def fetch_page(api_host, page, size=24):
    url = (f"https://{api_host}/swx/movie/search"
           f"?page={page}&size={size}&can_manko=true&most_popular=true")
    resp = json.loads(http_get(url))
    return json.loads(xn_decode(resp["data"]))


def to_item(d):
    tdn = d.get("title_display_name") or []
    en = next((x.get("title", "") for x in tdn if x.get("language") == "en"), "")
    title = en if en and en != d.get("title") else ""
    return {
        "code": d.get("title", ""),
        "title": title,
        "url": f"https://manko.fun/movie-info/{d.get('_id')}?series=false",
        "image": d.get("thumbnail_image") or d.get("wide_thumbnail") or "",
        "date": d.get("share_date") or "",
        "score": d.get("imdb_score") or 0,
    }


def main():
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    api_host = discover_api_base()
    print("API 域名:", api_host)
    items, seen = [], set()
    for p in range(1, pages + 1):
        data = fetch_page(api_host, p)
        print(f"page {p}: {len(data)} 条")
        for d in data:
            it = to_item(d)
            if it["url"] and it["url"] not in seen and it["image"]:
                seen.add(it["url"])
                items.append(it)
    # 按日期倒序
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    (BASE / "items.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写入 items.json: {len(items)} 条")

    # 重新生成 feed
    sys.path.insert(0, str(BASE))
    import build_feed
    build_feed.main()


if __name__ == "__main__":
    main()
