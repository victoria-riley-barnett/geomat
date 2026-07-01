# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

GeoMat is a FOSS geomaterialism visualization platform — think "FOSS Palantir MAVEN" for political economy analysis. It renders historical political and economic data across Europe (1450–1980) to make claims like unequal exchange empirically provable and queryable. The long-term vision includes ingesting real datasets (UN Comtrade, ILO, CShapes, Hickel et al.) to surface economic measurements on the map.

Currently: the visualization layer exists (MapLibre + timeline + economic heatmap), but the data pipeline is empty — `loadBoundaryData` returns empty features, no real GeoJSON is populated. The stall is always data, not rendering.

## Commands

```bash
npm run dev       # Vite dev server with hot reload
npm run build     # tsc + vite build (type errors will fail this)
npm run preview   # preview production build
npx tsc --noEmit  # type-check without building
```

No lint or test scripts are configured.

## Architecture

Two visualization modes:

**`src/main.ts`** — active, 2D MapLibre GL app
- Initializes map in a dynamically created `#map` container
- 4 map styles: Political, Terrain, Satellite, Economic (custom dark style in `public/styles/economic.json`)
- 8 historical periods (1450–1980) controlled by a time slider
- Asynchronously loads per-period data: boundaries from `public/data/boundaries/`, capital concentration from `public/data/capital/{year}.geojson`, narrative text from `public/content/{period}.md`
- Economic mode renders capital concentration as a heatmap scaled by `economic_weight`

**`src/globe.ts`** — extracted, not wired into `main.ts`
- Three.js + OrbitControls 3D globe with 4 texture views
- Ready to be integrated as a separate route/page

**Data layout** (most subdirs are empty stubs):
```
public/
  data/
    boundaries/    # historical political boundaries — needs CShapes data
    capital/       # capital concentration by year — needs real numbers
    trade/         # trade routes + railways — stub
    production/    # production sites — stub
    urban/         # city data — stub
  content/         # 8 Markdown files, one per period (narrative text)
  styles/
    economic.json  # custom MapLibre style (dark bg, heatmap config)
```

## Code conventions

- TypeScript strict mode: `noUnusedLocals`, `noUnusedParameters` — build will fail on unused vars
- `camelCase` for variables/functions, `PascalCase` for types (`MapStyle`, `TimePeriod`)
- Named imports for Three.js (`import * as three from 'three'`), default for MapLibre
- `try/catch` with `console.warn` for data-loading failures; never silent
- 2-space indentation, trailing commas in multiline objects/arrays
- No JSDoc

## Known issues and TODOs

- Terrain map style has CORS errors on the tile source (commented out)
- Region panel update disabled due to render loop errors
- `loadBoundaryData` returns empty FeatureCollection — needs CShapes GeoJSON
- Economic layer has no real data — needs Hickel et al. unequal exchange dataset or Comtrade-derived numbers
- Three.js (`globe.ts`) may not be in `package.json` — verify if adding globe functionality
