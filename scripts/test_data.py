#!/usr/bin/env python3
"""
test_data.py — Sanity checks for GeoMat synthesized output.

Two categories:

  DATA QUALITY — mechanical checks: no nulls, valid ranges, no duplicates.
    These catch broken pipelines.

  THEORETICAL EXPECTATIONS — the actual smoke test against our reading of the world.
    These encode world-systems expectations. If they fail, either the data is wrong
    or our formula is wrong. Both are worth knowing.

    These are NOT fixed ground truth. If the Hickel correction is added and UK 1914
    drops below the threshold, that's a signal to revisit the threshold, not a bug.
    Update the expectations to match your theoretical commitments.

Run: python3 scripts/test_data.py
Exit 0 = pass, Exit 1 = failures found.
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "public" / "data" / "capital"

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

failures = []


def check(condition: bool, description: str, detail: str = ""):
    if condition:
        print(f"  {PASS} {description}")
    else:
        msg = f"{description}" + (f": {detail}" if detail else "")
        print(f"  {FAIL} {msg}")
        failures.append(msg)


def load(year: int) -> list[dict]:
    path = DATA_DIR / f"{year}.geojson"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)["features"]


def props(features: list[dict]) -> list[dict]:
    return [f["properties"] for f in features]


def weight(features: list[dict], iso3: str) -> float | None:
    for f in features:
        if f["properties"].get("iso3") == iso3:
            return f["properties"]["economic_weight"]
    return None


def rank(features: list[dict], iso3: str) -> int | None:
    """Return 1-based rank by economic_weight descending."""
    sorted_feats = sorted(features, key=lambda f: f["properties"]["economic_weight"], reverse=True)
    for i, f in enumerate(sorted_feats):
        if f["properties"].get("iso3") == iso3:
            return i + 1
    return None


# ==================================================================================
# DATA QUALITY
# ==================================================================================

def test_quality(year: int):
    features = load(year)
    if not features:
        check(False, f"{year}: file missing or empty")
        return

    ps = props(features)
    iso3s = [p.get("iso3") for p in ps]

    check(len(features) >= 50, f"{year}: coverage >= 50 countries", f"got {len(features)}")

    weights = [p.get("economic_weight") for p in ps]
    check(all(w is not None for w in weights), f"{year}: no null weights")
    check(all(0.0 <= w <= 10.0 for w in weights if w is not None),
          f"{year}: all weights in [0, 10]",
          str([w for w in weights if w is not None and not (0 <= w <= 10)]))

    check(len(iso3s) == len(set(iso3s)), f"{year}: no duplicate ISO3 codes")

    for f in features:
        lng, lat = f["geometry"]["coordinates"]
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            check(False, f"{year}: invalid coordinates", f"iso3={f['properties'].get('iso3')} [{lng},{lat}]")
            return
    check(True, f"{year}: all coordinates valid")


# ==================================================================================
# THEORETICAL EXPECTATIONS (smoke tests against our reading)
# ==================================================================================
# Thresholds are intentionally loose — the point is to catch obviously wrong readings,
# not to over-specify the formula. Tighten as the formula matures.

def test_expectations_1980():
    year = 1980
    features = load(year)
    if not features:
        check(False, f"{year}: skipping expectations — no data")
        return

    # USA is the unambiguous Cold War hegemon
    usa = weight(features, "USA")
    check(usa is not None and usa >= 9.5,
          f"{year}: USA weight >= 9.5 (Cold War hegemon)", f"got {usa}")

    # USSR is a major power — command economy, huge territory, but inefficient
    # World Bank doesn't have USSR GDP; this will pass vacuously until Maddison is added
    ussr = weight(features, "SUN") or weight(features, "RUS")
    if ussr:
        check(ussr >= 6.0, f"{year}: USSR/Russia weight >= 6.0 (major power)", f"got {ussr}")

    # UK: declining imperial core, still top 5 but not what it was
    gbr = weight(features, "GBR")
    check(gbr is not None and 7.0 <= gbr <= 9.5,
          f"{year}: UK weight in [7, 9.5] (declining core)", f"got {gbr}")

    # West Germany: high industrial, export miracle
    deu = weight(features, "DEU")
    check(deu is not None and deu >= 8.0,
          f"{year}: Germany weight >= 8.0 (Wirtschaftswunder)", f"got {deu}")

    # India: large population, semi-periphery, GDP per capita very low
    ind = weight(features, "IND")
    gbr_rank = rank(features, "GBR")
    ind_rank = rank(features, "IND")
    if ind and gbr:
        check(gbr > ind,
              f"{year}: UK weight > India weight (core > semi-periphery)", f"UK={gbr} India={ind}")

    # Haiti: classic periphery — Caribbean plantation economy wreckage
    hti = weight(features, "HTI")
    if hti:
        check(hti < 4.0, f"{year}: Haiti weight < 4.0 (deep periphery)", f"got {hti}")

    # Saudi Arabia: oil boom 1980 — should punch above its GDP in world-system terms
    # (note: GDP-only formula will rate it by output, not strategic position — known limitation)
    sau = weight(features, "SAU")
    if sau:
        check(sau >= 5.0, f"{year}: Saudi Arabia weight >= 5.0 (petro-state boom)", f"got {sau}")

    # Core/periphery spread: ratio of top-10 mean to bottom-10 mean should be high
    sorted_w = sorted([f["properties"]["economic_weight"] for f in features], reverse=True)
    top10_mean = sum(sorted_w[:10]) / 10
    bot10_mean = sum(sorted_w[-10:]) / max(sum(1 for w in sorted_w[-10:] if w > 0), 1)
    check(top10_mean >= 3 * bot10_mean,
          f"{year}: core/periphery spread (top10 mean >= 3x bottom10 mean)",
          f"top10={top10_mean:.2f} bot10={bot10_mean:.2f}")


def test_historical_trajectory():
    """Cross-period checks: relative changes that should hold across any reasonable formula."""
    f1960 = load(1960)
    f1980 = load(1980)

    if not f1960 or not f1980:
        print("  [skip] historical trajectory — need both 1960 and 1980 data")
        return

    # USA rank should be #1 in both periods
    usa_rank_60 = rank(f1960, "USA")
    usa_rank_80 = rank(f1980, "USA")
    check(usa_rank_60 == 1, f"1960: USA ranked #1", f"got #{usa_rank_60}")
    check(usa_rank_80 == 1, f"1980: USA ranked #1", f"got #{usa_rank_80}")

    # Japan: dramatic rise — should rank higher in 1980 than 1960
    jpn_rank_60 = rank(f1960, "JPN")
    jpn_rank_80 = rank(f1980, "JPN")
    if jpn_rank_60 and jpn_rank_80:
        check(jpn_rank_80 < jpn_rank_60,
              f"Japan rank improved 1960→1980 (economic miracle)",
              f"1960=#{jpn_rank_60} 1980=#{jpn_rank_80}")

    # UK: should lose ground relative to Germany over this period
    gbr_60 = weight(f1960, "GBR")
    deu_60 = weight(f1960, "DEU")
    gbr_80 = weight(f1980, "GBR")
    deu_80 = weight(f1980, "DEU")
    if all(x is not None for x in [gbr_60, deu_60, gbr_80, deu_80]):
        gap_60 = gbr_60 - deu_60
        gap_80 = gbr_80 - deu_80
        check(gap_80 < gap_60,
              f"UK/Germany gap narrowed 1960→1980 (UK relative decline)",
              f"gap 1960={gap_60:.2f} 1980={gap_80:.2f}")


# ==================================================================================
# MAIN
# ==================================================================================

def main():
    print("GeoMat data tests\n")

    print("── Data quality ─────────────────────────────")
    for year in [1960, 1980]:
        test_quality(year)

    print("\n── Theoretical expectations: 1980 ──────────")
    test_expectations_1980()

    print("\n── Historical trajectory ────────────────────")
    test_historical_trajectory()

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        for f in failures:
            print(f"  • {f}")
        sys.exit(1)
    else:
        print(f"All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
