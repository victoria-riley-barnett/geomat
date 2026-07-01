#!/usr/bin/env python3
"""
synthesize.py — Combine raw source data into GeoMat economic weight index.

This is where GeoMat's reading lives. Raw sources are neutral (or pretend to be).
This script is explicitly not neutral — it applies a world-systems framework.

GEOMAT INDEX v0.1
=================
The economic_weight field represents capital accumulation density at a location,
calibrated to reflect world-system position, not just output volume.

Current formula:
  weight = log_normalize(GDP)

This is the baseline. It correlates well with core/periphery structure for the
modern era because capital concentration and GDP are deeply entangled. But it
conflates cause and effect — it measures accumulation, not the extraction that
produced it.

Planned corrections (add sources as they're ingested):
  - Hickel drain correction: subtract estimated surplus drain from peripheral weights.
    Empirically, this compresses the core/periphery gap upward for core countries
    (drain makes them look less productive than they are) and downward for periphery
    (makes their "low GDP" more visible as an imposed condition, not a natural state).
  - Comtrade trade surplus: reward net capital-goods exporters; weight reflects
    direction of surplus flow, not just volume.
  - Maddison historical GDP: extend coverage to 1870/1914/1938 periods currently
    using empty placeholder files.

FORMULA VERSIONING
==================
Bump SYNTHESIS_VERSION when formula changes. This gets embedded in the output
GeoJSON so git history tells you exactly which formula produced which file.

PERIOD → SOURCE MAPPING
========================
  1980: World Bank GDP (direct)
  1960: World Bank GDP (direct, used as proxy if needed)
  1938: Maddison Project (not yet ingested — TODO)
  1914: Maddison Project (not yet ingested — TODO)
  1870: Maddison Project (not yet ingested — TODO)
  1700, 1550, 1450: No GDP data exists. Urban population (Bairoch 1982) is the
    best available proxy for pre-industrial capital concentration. TODO.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR  = Path(__file__).parent.parent / "public" / "data" / "raw"
OUT_DIR  = Path(__file__).parent.parent / "public" / "data" / "capital"
SYNTHESIS_VERSION = "0.1.0"

# Source weights — explicit theoretical commitments.
# These will sum/interact as more sources are added.
# Adjust here when adding Hickel, Comtrade, etc.
FORMULA = {
    "gdp_log_normalized": 1.0,
    # "hickel_drain_correction": -0.3,   # planned: penalize extracted surplus
    # "comtrade_net_surplus":    0.1,    # planned: reward capital-goods export surplus
}


# --- normalization ----------------------------------------------------------------

def log_normalize(values: list[float], out_min=0.5, out_max=10.0) -> list[float]:
    """Log-normalize positive floats to [out_min, out_max].
    Log scale is load-bearing: GDP spans 4-5 orders of magnitude between
    core and periphery. Linear normalization would collapse most of the world to ~0.
    """
    logs = [math.log10(v) for v in values if v and v > 0]
    if not logs:
        return [0.0] * len(values)
    lo, hi = min(logs), max(logs)
    result = []
    for v in values:
        if not v or v <= 0:
            result.append(0.0)
        elif hi == lo:
            result.append(out_max)
        else:
            normed = (math.log10(v) - lo) / (hi - lo)
            result.append(round(out_min + normed * (out_max - out_min), 3))
    return result


# --- source loaders ---------------------------------------------------------------

def load_raw(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_worldbank_gdp(year: int) -> dict[str, float]:
    path = RAW_DIR / "worldbank" / f"gdp_{year}.json"
    if not path.exists():
        print(f"  [warn] no WB GDP data for {year}, run fetch_worldbank.py first")
        return {}
    raw = load_raw(path)
    return {k: v for k, v in raw["data"].items() if v and v > 0}


def load_worldbank_countries() -> dict[str, dict]:
    path = RAW_DIR / "worldbank" / "countries.json"
    if not path.exists():
        raise FileNotFoundError("Run scripts/sources/fetch_worldbank.py first")
    return load_raw(path)["data"]


# --- synthesis --------------------------------------------------------------------

def synthesize_year(year: int, countries: dict[str, dict]) -> dict:
    """Build GeoMat index for a given year from all available sources."""

    # --- GDP base (World Bank) ---
    gdp = load_worldbank_gdp(year)

    # Planned: load Hickel drain data for this year
    # hickel = load_hickel(year)

    # Planned: load Comtrade net surplus for this year
    # comtrade = load_comtrade(year)

    # Build entry list: only countries with GDP data AND coordinates
    entries = []
    gdp_values = []
    for iso3, gdp_val in gdp.items():
        meta = countries.get(iso3)
        if not meta:
            continue
        entries.append((iso3, gdp_val, meta))
        gdp_values.append(gdp_val)

    if not entries:
        return {"type": "FeatureCollection", "features": []}

    normalized_gdp = log_normalize(gdp_values)

    features = []
    for (iso3, gdp_val, meta), gdp_norm in zip(entries, normalized_gdp):

        # Composite score — currently just GDP, structured for extension
        score = gdp_norm * FORMULA["gdp_log_normalized"]

        # Planned:
        # drain = hickel.get(iso3, 0)
        # score += drain * FORMULA["hickel_drain_correction"]

        score = round(max(0.0, min(10.0, score)), 3)

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
                "region": meta.get("region", ""),
                "economic_weight": score,
                # Source components — keep these for debugging and future correction
                "gdp_usd": gdp_val,
                "gdp_norm": gdp_norm,
                # Planned: "hickel_drain": drain,
                "synthesis_version": SYNTHESIS_VERSION,
                "synthesis_formula": list(FORMULA.keys()),
            },
        })

    return {"type": "FeatureCollection", "features": features}


# --- output -----------------------------------------------------------------------

def load_existing_weights(year: int) -> dict[str, float]:
    path = OUT_DIR / f"{year}.geojson"
    if not path.exists():
        return {}
    with open(path) as f:
        fc = json.load(f)
    return {
        feat["properties"]["iso3"]: feat["properties"]["economic_weight"]
        for feat in fc["features"]
        if "iso3" in feat["properties"]
    }


def diff_report(old: dict[str, float], new_features: list) -> str:
    new = {f["properties"]["iso3"]: f["properties"]["economic_weight"]
           for f in new_features if "iso3" in f["properties"]}
    added   = set(new) - set(old)
    removed = set(old) - set(new)
    shifted = {k for k in set(old) & set(new) if abs(old[k] - new[k]) > 0.05}
    if not added and not removed and not shifted:
        return "no meaningful change"
    parts = []
    if added:   parts.append(f"+{len(added)} countries")
    if removed: parts.append(f"-{len(removed)} countries")
    if shifted:
        top = sorted(shifted, key=lambda k: abs(new[k] - old[k]), reverse=True)[:3]
        parts.append(f"{len(shifted)} weights shifted (largest: {', '.join(top)})")
    return ", ".join(parts)


def write_geojson(fc: dict, year: int):
    old_weights = load_existing_weights(year)
    report = diff_report(old_weights, fc["features"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{year}.geojson"
    with open(path, "w") as f:
        json.dump(fc, f, indent=2)
    print(f"  {year}: {report} → {len(fc['features'])} features  [formula v{SYNTHESIS_VERSION}]")


# --- period mapping ---------------------------------------------------------------

# Map our app's time periods to available source years.
# When Maddison is ingested, add entries for 1870/1914/1938.
PERIOD_SOURCE_YEAR = {
    "late-feudal":      None,   # 1450 — no GDP data; TODO: Bairoch urban population
    "early-modern":     None,   # 1550 — no GDP data
    "mercantile":       None,   # 1700 — no GDP data
    "early-industrial": None,   # 1800 — no GDP data
    "high-industrial":  None,   # 1870 — TODO: Maddison
    "imperial":         None,   # 1914 — TODO: Maddison
    "interwar":         None,   # 1938 — TODO: Maddison
    "cold-war":         1980,   # World Bank direct
}


def main():
    print(f"GeoMat synthesize.py v{SYNTHESIS_VERSION}")
    print(f"Formula weights: {FORMULA}\n")

    print("Loading country metadata...")
    countries = load_worldbank_countries()
    print(f"  {len(countries)} countries with coordinates\n")

    synthesized_years = set()
    for period, source_year in PERIOD_SOURCE_YEAR.items():
        if source_year is None:
            print(f"  {period}: no source data yet, skipping")
            continue
        if source_year in synthesized_years:
            continue
        synthesized_years.add(source_year)
        fc = synthesize_year(source_year, countries)
        write_geojson(fc, source_year)

    print("\nDone.")
    print("Next sources to add:")
    print("  - Maddison Project (1870/1914/1938): https://www.rug.nl/ggdc/historicaldevelopment/maddison/")
    print("  - Hickel et al. drain dataset: https://doi.org/10.1016/j.gloenvcha.2022.102507")
    print("  - Bairoch urban pop (pre-1800): manual digitization or existing GIS dataset")


if __name__ == "__main__":
    main()
