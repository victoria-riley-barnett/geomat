# Geomaterialism 

- Need a visualizer that can take in geo-objects
- Asset catalogue https://stacspec.org/en
- MapWeave closed source, int/viz focused
	- Would prefer OSS, and more general

## Vision: Historical/Geographic/Dialectical Materialism Tool
Interactive globe allowing zoom into any spot on Earth to explore:
- Geographic/topographic features
- Political boundaries (current + historical)
- Ethnic/cultural regions  
- How geography relates to present-day politics/economics

## Current Implementation
- **Dev Controls (Left)**: Position, rotation, lighting, camera
- **User Controls (Bottom)**: Political, Geographic, Night Lights, Topography
- **Tech**: MapLibre GL (vector tiles + terrain)

## High-Res Strategy for Detail Zooming

### Tile-Based (RECOMMENDED)
- **Cesium.js**: Built for streaming high-res tiles
- **Sources**: Mapbox, OpenStreetMap, Natural Earth Data
- Load tiles dynamically based on zoom level

### Ultra High-Res Textures
- **Political**: Natural Earth 1:10m vectors → 8K+ render
- **Satellite**: NASA Blue Marble NG (86400x43200px)
- **Topo**: GEBCO 2023, SRTM elevation

### Vector Overlays (no pixelation)
- GeoJSON political/ethnic boundaries
- Rendered as line geometries on globe
- Sources: Natural Earth, CShapes (historical), Ethnologue

## Data Sources
- **Historical borders**: CShapes dataset
- **Ethnic/linguistic**: Ethnologue, Joshua Project
- **Material/economic**: World Bank, ACLED, resource deposits

## Tools
- Geoquery? https://www.aiddata.org/geoquery
- Geoda https://geodacenter.github.io/
- D3js perhaps https://d3js.org/
- Maplibre https://maplibre.org/maplibre-gl-js/docs/
- Openglobus https://openglobus.org/


## Sources
- China
	- Global China Initiative https://www.bu.edu/gdp/chinas-overseas-development-finance/
	- https://www.bu.edu/gdp/research/gci/
	- Is https://www.china-data-online.com/acmr-cndata-pub/ reliable?
- World Bank
	- https://data.worldbank.org/
	- https://datacatalog.worldbank.org/home
- 
