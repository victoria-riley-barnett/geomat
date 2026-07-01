#!/usr/bin/env python3
"""
fetch_capital.py — Generate capital concentration GeoJSON from World Bank GDP data.

Data source: World Bank API (NY.GDP.MKTP.CD — GDP at market prices, current USD)
Coordinates: World Bank Countries API (has lat/lng and capital city name)

METHODOLOGY NOTE:
GDP is a capitalist accounting unit with known biases:
  - Systematically undercounts subsistence and care economies (periphery)
  - Inflates financial sector value (core)
  - Uses market exchange rates, which overstate core purchasing power vs. PPP
This makes it a reasonable first-pass proxy for capital accumulation at the
national level, but underestimates unequal exchange depth. Supplement with:
  - Trade flow data (UN Comtrade) for embodied labor/resource transfer
  - Hickel et al. unequal exchange dataset for corrected drain estimates

HISTORICAL COVERAGE:
  - 1980: Direct World Bank data
  - 1960: Direct World Bank data (reasonable proxy for cold-war period)
  - Pre-1960: World Bank has no data. Use Maddison Project Database instead:
    https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023
    (Manual CSV download, then adapt maddison_to_geojson() below)

OUTPUTS: public/data/capital/{year}.geojson
  Properties per feature:
    name: capital city name
    country: country name
    iso2: ISO 2-letter code
    economic_weight: float 0-10, log-normalized from GDP
    gdp_usd: raw GDP in current USD
    source: data source string
"""

import json
import math
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data" / "capital"

WB_API = "https://api.worldbank.org/v2"
GDP_INDICATOR = "NY.GDP.MKTP.CD"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_country_metadata() -> dict[str, dict]:
    """Fetch all countries from World Bank API with coordinates and capital names."""
    url = f"{WB_API}/country?format=json&per_page=300"
    data = fetch_json(url)
    countries = {}
    for c in data[1]:
        if not c.get("latitude") or not c.get("longitude"):
            continue
        countries[c["id"]] = {
            "name": c["name"],
            "capital": c.get("capitalCity", ""),
            "lat": float(c["latitude"]),
            "lng": float(c["longitude"]),
            "region": c.get("region", {}).get("value", ""),
        }
    return countries


def fetch_gdp_for_year(year: int) -> dict[str, float]:
    """Fetch GDP (NY.GDP.MKTP.CD) for all countries in a given year."""
    url = f"{WB_API}/country/all/indicator/{GDP_INDICATOR}?date={year}&format=json&per_page=300"
    data = fetch_json(url)
    gdp = {}
    if not data or len(data) < 2 or data[1] is None:
        return gdp
    for entry in data[1]:
        if entry.get("value") is not None:
            gdp[entry["countryiso3code"]] = entry["value"]
    return gdp


def log_normalize(values: list[float], out_min=0.5, out_max=10.0) -> list[float]:
    """Log-normalize a list of positive floats to [out_min, out_max].
    Log scale is appropriate because GDP spans orders of magnitude between
    core and periphery — linear normalization would collapse peripheral weights to ~0.
    """
    logs = [math.log10(v) for v in values if v > 0]
    lo, hi = min(logs), max(logs)
    result = []
    for v in values:
        if v <= 0:
            result.append(0.0)
        else:
            normed = (math.log10(v) - lo) / (hi - lo)
            result.append(round(out_min + normed * (out_max - out_min), 2))
    return result


# ISO3 → ISO2 mapping isn't in WB countries API directly, but ISO3 is the WB country code
# WB GDP uses ISO3; WB country metadata uses ISO2 as the id. Build a bridge.
def build_iso_bridge(country_meta: dict) -> dict[str, str]:
    """Map ISO3 → ISO2 using the WB country API's 'id' (ISO2) field.
    The WB GDP indicator uses ISO3 codes; the country list uses ISO2 as keys.
    We need to join them. The WB country endpoint also exposes iso2Code per entry,
    but we need a second pass since our metadata dict is keyed by ISO2.
    """
    # Refetch to get iso3 codes too
    url = f"{WB_API}/country?format=json&per_page=300"
    data = fetch_json(url)
    bridge = {}  # iso3 -> iso2
    for c in data[1]:
        if c.get("id") and c.get("iso2Code"):
            # WB: 'id' is actually the 3-letter code in this context
            # Let's check: WB uses 3-letter in some endpoints, 2-letter in others
            # country endpoint: id=iso2, iso2Code=iso2 (same), but no iso3 field exposed directly
            pass
    # Actually WB country API: 'id' is the 2-letter code, there's no iso3 in that endpoint.
    # The GDP indicator returns 'countryiso3code'. We need to match by name or use a static map.
    # Build iso3->iso2 from name matching as fallback; for now return empty and match by lookup.
    return bridge


def gdp_to_geojson(gdp: dict[str, float], country_meta: dict, year: int) -> dict:
    """Build GeoJSON FeatureCollection from GDP data joined with country coordinates."""
    # WB GDP uses ISO3 codes. Country metadata is keyed by WB's own ID (mix of ISO2/ISO3).
    # The WB country API actually uses its own codes. We'll match by fetching a proper mapping.

    # Simpler approach: fetch the country list again with iso3 info embedded
    url = f"{WB_API}/country?format=json&per_page=300&source=2"
    # iso3 is embedded in each country entry as part of the response
    # Actually let's just rebuild with the iso3 from a direct hit
    iso3_meta = fetch_iso3_metadata()

    features = []
    weights_raw = []
    entries = []

    for iso3, gdp_val in gdp.items():
        meta = iso3_meta.get(iso3)
        if not meta or gdp_val <= 0:
            continue
        if not meta.get("lat") or not meta.get("lng"):
            continue
        entries.append((iso3, gdp_val, meta))
        weights_raw.append(gdp_val)

    normalized = log_normalize(weights_raw)

    for (iso3, gdp_val, meta), weight in zip(entries, normalized):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [meta["lng"], meta["lat"]],
            },
            "properties": {
                "name": meta["capital"] or meta["name"],
                "country": meta["name"],
                "iso3": iso3,
                "economic_weight": weight,
                "gdp_usd": gdp_val,
                "source": f"World Bank NY.GDP.MKTP.CD {year}",
            },
        })

    return {"type": "FeatureCollection", "features": features}


def fetch_iso3_metadata() -> dict[str, dict]:
    """Fetch country metadata keyed by ISO3 code.
    WB's /country endpoint uses its own ID scheme, but /country/{iso3} works per-country.
    Better: use the lending groups endpoint which exposes iso3 codes in the country list.
    """
    # The cleanest approach: WB /country?format=json gives us entries where
    # 'id' is their 2-3 letter code. For large countries it's 3-letter ISO3.
    # For the GDP join we need ISO3. Use the indicator response's countryiso3code
    # to look up country info via /country/{iso3}.
    # For efficiency, fetch the full country list and index by id (which is often ISO3 for non-aggregate).
    url = f"{WB_API}/country?format=json&per_page=300"
    data = fetch_json(url)
    meta = {}
    for c in data[1]:
        cid = c.get("id", "")
        if len(cid) == 3 and c.get("latitude"):  # 3-letter = real country, not aggregate
            meta[cid] = {
                "name": c["name"],
                "capital": c.get("capitalCity", ""),
                "lat": float(c["latitude"]),
                "lng": float(c["longitude"]),
            }
    return meta


def load_existing(year: int) -> dict | None:
    path = OUTPUT_DIR / f"{year}.geojson"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def diff_summary(old: dict | None, new: dict) -> str:
    if old is None:
        return f"new file, {len(new['features'])} features"
    old_by_iso = {f["properties"]["iso3"]: f["properties"]["economic_weight"]
                  for f in old["features"]}
    new_by_iso = {f["properties"]["iso3"]: f["properties"]["economic_weight"]
                  for f in new["features"]}
    added   = set(new_by_iso) - set(old_by_iso)
    removed = set(old_by_iso) - set(new_by_iso)
    shifted = {k for k in old_by_iso.keys() & new_by_iso.keys()
               if abs(old_by_iso[k] - new_by_iso[k]) > 0.1}
    if not added and not removed and not shifted:
        return "no meaningful change"
    parts = []
    if added:   parts.append(f"+{len(added)} countries")
    if removed: parts.append(f"-{len(removed)} countries")
    if shifted: parts.append(f"{len(shifted)} weights shifted >0.1")
    return ", ".join(parts)


def write_geojson(fc: dict, year: int):
    path = OUTPUT_DIR / f"{year}.geojson"
    old = load_existing(year)
    summary = diff_summary(old, fc)
    with open(path, "w") as f:
        json.dump(fc, f, indent=2)
    print(f"  {year}: {summary} → {len(fc['features'])} features written")


def main():
    print("Fetching country metadata...")
    iso3_meta = fetch_iso3_metadata()
    print(f"  Got {len(iso3_meta)} countries with coordinates")

    # Years with direct World Bank data
    wb_years = [1960, 1980]

    for year in wb_years:
        print(f"\nFetching GDP for {year}...")
        gdp = fetch_gdp_for_year(year)
        print(f"  Got {len(gdp)} GDP entries")

        features = []
        weights_raw = []
        entries = []

        for iso3, gdp_val in gdp.items():
            meta = iso3_meta.get(iso3)
            if not meta or gdp_val <= 0:
                continue
            entries.append((iso3, gdp_val, meta))
            weights_raw.append(gdp_val)

        normalized = log_normalize(weights_raw)

        for (iso3, gdp_val, meta), weight in zip(entries, normalized):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [meta["lng"], meta["lat"]],
                },
                "properties": {
                    "name": meta["capital"] or meta["name"],
                    "country": meta["name"],
                    "iso3": iso3,
                    "economic_weight": weight,
                    "gdp_usd": gdp_val,
                    "source": f"World Bank {GDP_INDICATOR} {year}",
                },
            })

        fc = {"type": "FeatureCollection", "features": features}

        # Map to our period file names
        # 1960 → used as proxy for 'cold-war' 1980 period if 1980 data is thin
        # 1980 → primary cold-war data
        write_geojson(fc, year)

    print("\nDone. For pre-1960 periods, see Maddison Project:")
    print("  https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023")
    print("  Download the Excel file and adapt maddison_to_geojson() (not yet implemented).")
    print("\nFor unequal exchange weights (corrected for drain), see Hickel et al.:")
    print("  https://doi.org/10.1016/j.gloenvcha.2022.102507 (supplementary dataset)")


if __name__ == "__main__":
    main()
