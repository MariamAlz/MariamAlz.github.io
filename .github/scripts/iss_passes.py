"""Save the next ISS passes over Abu Dhabi to assets/iss.json.

The site shows the next one under the sky plot. Orbit from CelesTrak (TLE),
propagated with SGP4. A pass is "visible" when the ISS is sunlit while the sky
in Abu Dhabi is dark (sun at least 6 degrees below the horizon).
Runs twice a day, since ISS reboosts shift pass times by a minute or so.
"""
import datetime
import json
import math
import os
import urllib.request

from sgp4.api import Satrec, jday

LAT, LON, ALT_KM = 24.4539, 54.3773, 0.0
MASK = 10.0  # degrees above the horizon
DAYS = 10
STEP = 10  # seconds
RE = 6378.137
D2R = math.pi / 180


def fetch_tle():
    url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"
    req = urllib.request.Request(url, headers={"User-Agent": "mariamalzaabi.ae ISS passes"})
    with urllib.request.urlopen(req, timeout=30) as r:
        lines = [l.strip() for l in r.read().decode().splitlines() if l.strip()]
    l1 = next(l for l in lines if l.startswith("1 "))
    l2 = next(l for l in lines if l.startswith("2 "))
    return l1, l2


def gmst(jd):
    t = (jd - 2451545.0) / 36525
    g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - t ** 3 / 38710000
    return (g % 360) * D2R


def sun_eci(jd):
    # low precision solar position (Astronomical Almanac), unit vector
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360
    g = (357.528 + 0.9856003 * n) % 360 * D2R
    lam = (L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) * D2R
    eps = (23.439 - 0.0000004 * n) * D2R
    return (math.cos(lam), math.cos(eps) * math.sin(lam), math.sin(eps) * math.sin(lam))


def observer():
    lat, lon = LAT * D2R, LON * D2R
    e2 = 0.00669437999014
    N = RE / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    pos = ((N + ALT_KM) * math.cos(lat) * math.cos(lon), (N + ALT_KM) * math.cos(lat) * math.sin(lon),
           (N * (1 - e2) + ALT_KM) * math.sin(lat))
    east = (-math.sin(lon), math.cos(lon), 0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    up = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
    return pos, east, north, up


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def rot_z(v, th):
    # ECI (TEME) to Earth-fixed: rotate by -GMST
    c, s = math.cos(th), math.sin(th)
    return (c * v[0] + s * v[1], -s * v[0] + c * v[1], v[2])


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def passes(sat, start):
    obs, east, north, up = observer()
    out, cur = [], None
    for k in range(DAYS * 86400 // STEP):
        t = start + datetime.timedelta(seconds=k * STEP)
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second)
        err, r, _ = sat.sgp4(jd, fr)
        if err:
            continue
        th = gmst(jd + fr)
        ecef = rot_z(r, th)
        d = (ecef[0] - obs[0], ecef[1] - obs[1], ecef[2] - obs[2])
        rng = math.sqrt(dot(d, d))
        el = math.asin(dot(d, up) / rng) / D2R
        az = math.atan2(dot(d, east), dot(d, north)) / D2R % 360
        if el >= MASK:
            s = sun_eci(jd + fr)
            # ISS in Earth's shadow (cylinder model)?
            p = dot(r, s)
            perp = math.sqrt(max(0.0, dot(r, r) - p * p))
            lit = p > 0 or perp > RE
            dark = math.asin(dot(rot_z(s, th), up)) / D2R < -6
            if cur is None:
                cur = {"start": iso(t), "startAz": round(az), "max": iso(t), "maxEl": el, "visible": False}
            if el > cur["maxEl"]:
                cur["max"], cur["maxEl"] = iso(t), el
            cur["end"], cur["endAz"] = iso(t), round(az)
            if lit and dark:
                cur["visible"] = True
        elif cur is not None:
            cur["maxEl"] = round(cur["maxEl"])
            out.append(cur)
            cur = None
    return out


def main():
    l1, l2 = fetch_tle() if not os.environ.get("ISS_TLE") else os.environ["ISS_TLE"].split("|")
    sat = Satrec.twoline2rv(l1, l2)
    start = os.environ.get("ISS_START")
    start = datetime.datetime.fromisoformat(start) if start else datetime.datetime.now(datetime.timezone.utc)
    start = start.replace(microsecond=0)
    found = passes(sat, start)
    if not found:
        raise SystemExit("No passes found, keeping the old file")
    out = {"updated": iso(datetime.datetime.now(datetime.timezone.utc)), "passes": found}
    with open("assets/iss.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print("Saved", len(found), "passes,", sum(p["visible"] for p in found), "visible")


if __name__ == "__main__":
    main()
