"""Refresh assets/mission-log.json from Last.fm and Letterboxd.

Each source is used only when its username is set; otherwise the current
entry in the JSON file is kept as it is. Reviews are never copied.
"""
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

PATH = "assets/mission-log.json"
UA = {"User-Agent": "mariamalzaabi.ae mission log"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read()


def lastfm(user, key):
    q = urllib.parse.urlencode({"method": "user.getrecenttracks", "user": user, "api_key": key, "format": "json", "limit": 1})
    tracks = json.loads(get("https://ws.audioscrobbler.com/2.0/?" + q))["recenttracks"]["track"]
    t = tracks[0] if isinstance(tracks, list) else tracks
    return {
        "title": t["name"],
        "artist": t["artist"]["#text"],
        "nowplaying": t.get("@attr", {}).get("nowplaying") == "true",
    }


def letterboxd(user):
    ns = {"lb": "https://letterboxd.com"}
    root = ET.fromstring(get("https://letterboxd.com/%s/rss/" % urllib.parse.quote(user)))
    for item in root.iter("item"):
        title = item.findtext("lb:filmTitle", namespaces=ns)
        if title:  # skips list entries, which have no film title
            rating = item.findtext("lb:memberRating", namespaces=ns)
            return {"title": title, "rating": float(rating) if rating else 0}
    return None


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    user, key = os.environ.get("LASTFM_USER"), os.environ.get("LASTFM_KEY")
    if user and key:
        try:
            data["music"] = lastfm(user, key)
        except Exception as e:
            print("Last.fm skipped:", e)
    lb = os.environ.get("LETTERBOXD_USER")
    if lb:
        try:
            data["film"] = letterboxd(lb) or data.get("film")
        except Exception as e:
            print("Letterboxd skipped:", e)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
