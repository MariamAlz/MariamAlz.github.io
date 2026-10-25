"""Save current GPS, Galileo and BeiDou orbital elements to assets/gnss.json.

The site propagates these in the browser to draw the live sky over Abu Dhabi.
Data: CelesTrak GP (OMM JSON). Runs once a day, which is plenty for MEO orbits.
"""
import datetime
import json
import re
import urllib.request

GROUPS = {"G": "gps-ops", "E": "galileo", "C": "beidou"}
PRN = {"G": r"PRN (\d+)", "E": r"PRN\s*E?(\d+)", "C": r"\(C(\d+)\)"}


def fetch(group):
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=%s&FORMAT=json" % group
    req = urllib.request.Request(url, headers={"User-Agent": "mariamalzaabi.ae sky plot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    sats = []
    for prefix, group in GROUPS.items():
        for o in fetch(group):
            m = re.search(PRN[prefix], o["OBJECT_NAME"])
            sats.append({
                "id": "%s%02d" % (prefix, int(m.group(1))) if m else "%s%d" % (prefix, o["NORAD_CAT_ID"] % 100),
                "epoch": o["EPOCH"] + "Z",
                "n": o["MEAN_MOTION"], "e": o["ECCENTRICITY"], "i": o["INCLINATION"],
                "raan": o["RA_OF_ASC_NODE"], "argp": o["ARG_OF_PERICENTER"], "ma": o["MEAN_ANOMALY"],
            })
    if len(sats) < 30:
        raise SystemExit("Only %d satellites returned, keeping the old file" % len(sats))
    sats.sort(key=lambda s: s["id"])
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sats": sats}
    with open("assets/gnss.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print("Saved", len(sats), "satellites")


if __name__ == "__main__":
    main()
