"""Save the latest Medium posts to assets/medium.json for the Writing section."""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

FEED = "https://medium.com/feed/@mariam-alzaabi"
NS = {"content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}


def text(s, n):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: s.rfind(" ", 0, n)] + "…"


def main():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0 (mariamalzaabi.ae writing feed)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    posts = []
    for item in root.iter("item"):
        body = item.findtext("content:encoded", default="", namespaces=NS)
        img = re.search(r'<img[^>]+src="([^"]+)"', body)
        posts.append({
            "title": item.findtext("title", "").strip(),
            "url": item.findtext("link", "").split("?")[0],
            "date": item.findtext("pubDate", ""),
            "tags": [c.text for c in item.findall("category")][:3],
            "excerpt": text(body, 180),
            "image": img.group(1) if img else None,
        })
    print("Found", len(posts), "posts")
    with open("assets/medium.json", "w", encoding="utf-8") as f:
        json.dump({"posts": posts[:6]}, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
