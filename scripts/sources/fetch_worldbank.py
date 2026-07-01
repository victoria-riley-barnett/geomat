#!/usr/bin/env python3
"""
Fetch World Bank data and save to public/data/raw/worldbank/.

Saves raw API responses — no transformation here, that's synthesize.py's job.

Outputs:
  public/data/raw/worldbank/countries.json   — coordinates + capital names for all countries
  public/data/raw/worldbank/gdp_{year}.json  — GDP (NY.GDP.MKTP.CD) per country for each year
"""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent.parent / "public" / "data" / "raw" / "worldbank"
WB_API = "https://api.worldbank.org/v2"
GDP_INDICATOR = "NY.GDP.MKTP.CD"

# Years with direct World Bank coverage
FETCH_YEARS = [1960, 1980]


def fetch_json(url: str) -> list | dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_countries() -> dict[str, dict]:
    """Fetch all country metadata: name, capital, lat, lng keyed by ISO3."""
    url = f"{WB_API}/country?format=json&per_page=300"
    data = fetch_json(url)
    countries = {}
    for c in data[1]:
        cid = c.get("id", "")
        if len(cid) == 3 and c.get("latitude") and c.get("longitude"):
            countries[cid] = {
                "name": c["name"],
                "capital": c.get("capitalCity", ""),
                "lat": float(c["latitude"]),
                "lng": float(c["longitude"]),
                "region": c.get("region", {}).get("value", ""),
                "income_level": c.get("incomeLevel", {}).get("value", ""),
            }
    return countries


def fetch_gdp(year: int) -> dict[str, float | None]:
    """Fetch GDP (NY.GDP.MKTP.CD) for all countries in a given year."""
    url = f"{WB_API}/country/all/indicator/{GDP_INDICATOR}?date={year}&format=json&per_page=300"
    data = fetch_json(url)
    if not data or len(data) < 2 or data[1] is None:
        return {}
    return {
        entry["countryiso3code"]: entry["value"]
        for entry in data[1]
        if entry.get("countryiso3code")
    }


def save(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  saved {path.name} ({len(payload.get('data', payload))} entries)")


def main():
    print("Fetching country metadata...")
    countries = fetch_countries()
    save(RAW_DIR / "countries.json", {
        "source": "World Bank Countries API",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": countries,
    })

    for year in FETCH_YEARS:
        print(f"Fetching GDP {year}...")
        gdp = fetch_gdp(year)
        save(RAW_DIR / f"gdp_{year}.json", {
            "source": f"World Bank {GDP_INDICATOR}",
            "indicator": GDP_INDICATOR,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "year": year,
            "data": gdp,
        })


if __name__ == "__main__":
    main()
