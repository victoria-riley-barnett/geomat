# Agent Guidelines for geomat

## Build/Lint/Test Commands
- `npm run dev` – Start development server (Vite)
- `npm run build` – TypeScript compile and Vite build
- `npm run preview` – Preview production build
- No lint or test scripts defined; consider adding `tsc --noEmit` for type‑checking.

## Code Style Guidelines
- **TypeScript**: Strict mode enabled (`noUnusedLocals`, `noUnusedParameters`). Use explicit types.
- **Imports**: ES modules (`type: "module"`). Use named imports for Three.js (`import * as three from 'three'`), default for MapLibre (`import maplibregl from 'maplibre-gl'`).
- **Naming**: camelCase for variables/functions (`currentMapStyle`), PascalCase for types/aliases (`MapStyle`, `TimePeriod`). Constants may be camelCase (`mapStyles`).
- **Formatting**: No formatter configured; follow existing indentation (2 spaces). Use trailing commas in multiline objects/arrays.
- **Error Handling**: Use `try`/`catch` with `console.warn` for data‑loading failures; avoid silent failures.
- **File Structure**: Keep source files in `src/`. Static assets in `public/`. GeoJSON data in `public/data/`.
- **Comments**: Minimal; use `//` for single‑line notes. No JSDoc required.

## Project‑Specific Notes
- The app uses MapLibre GL for 2D maps and Three.js for 3D globe.
- Historical period data is loaded from `public/content/*.md` and `public/data/*.geojson`.
- Custom map styles are defined in `public/styles/economic.json`.

## When Adding Features
- Ensure the TypeScript compilation passes (`npm run build`).
- Verify that the Vite dev server still works.
- If adding new dependencies, update `package.json` with exact versions.
- No existing test suite; add unit tests for new utilities if appropriate.