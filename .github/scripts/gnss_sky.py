"""Save current GPS, Galileo and BeiDou orbital elements to assets/gnss.json.

The site propagates these in the browser to draw the live sky over Abu Dhabi.
Data: CelesTrak GP (OMM JSON). Runs once a day, which is plenty for MEO orbits.
"""
import datetime
import json
import re
import urllib.request

GROUPS = {"G": "gps-ops", "E": "galileo", "C": "beidou"}
PRN = {"G": r"PRN (\d+)", "C": r"\(C(\d+)\)"}
# CelesTrak names Galileo satellites by GSAT number, so map those to their PRN.
# Newer satellites missing here keep their GSAT number as the label.
GALILEO_PRN = {
    "0101": 11, "0102": 12, "0103": 19, "0104": 20, "0201": 18, "0202": 14, "0203": 26, "0204": 22,
    "0205": 24, "0206": 30, "0207": 7, "0208": 8, "0209": 9, "0210": 1, "0211": 2, "0212": 3,
    "0213": 4, "0214": 5, "0215": 21, "0216": 25, "0217": 27, "0218": 31, "0219": 36, "0220": 13,
    "0221": 15, "0222": 33, "0223": 34, "0224": 10,
}


def label(prefix, name, norad):
    if prefix == "E":
        g = re.search(r"GSAT(\d{4})", name)
        if g and g.group(1) in GALILEO_PRN:
            return "E%02d" % GALILEO_PRN[g.group(1)]
        return "GSAT" + g.group(1)[1:] if g else "E%d" % (norad % 100)
    m = re.search(PRN[prefix], name)
    if not m:
        print("No PRN in name:", name)
    return "%s%02d" % (prefix, int(m.group(1))) if m else "%s%d" % (prefix, norad % 100)


def fetch(group):
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=%s&FORMAT=json" % group
    req = urllib.request.Request(url, headers={"User-Agent": "mariamalzaabi.ae sky plot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    sats = []
    for prefix, group in GROUPS.items():
        for o in fetch(group):
            sats.append({
                "id": label(prefix, o["OBJECT_NAME"], o["NORAD_CAT_ID"]),
                "epoch": o["EPOCH"] + "Z",
                "n": o["MEAN_MOTION"], "e": o["ECCENTRICITY"], "i": o["INCLINATION"],
                "raan": o["RA_OF_ASC_NODE"], "argp": o["ARG_OF_PERICENTER"], "ma": o["MEAN_ANOMALY"],
            })
    if len(sats) < 30:
        raise SystemExit("Only %d satellites returned, keeping the old file" % len(sats))
    sats.sort(key=lambda s: s["id"])
    for s in sats:
        s["c"] = s["id"][0] if s["id"][0] in "GEC" else "E"
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sats": sats}
    with open("assets/gnss.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print("Saved", len(sats), "satellites")


if __name__ == "__main__":
    main()
