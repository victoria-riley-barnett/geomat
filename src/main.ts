import './style.css'
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// GeoMat - Historical Geography Visualization
// Map container
const mapContainer = document.createElement('div');
mapContainer.id = 'map';
document.body.appendChild(mapContainer);

let map: maplibregl.Map | null = null;

// Map styles using OpenFreeMap's available styles
type MapStyle = 'political' | 'terrain' | 'satellite' | 'economic';
const mapStyles: Record<MapStyle, { name: string; url: string; }> = {
    political: {
        name: 'Political Boundaries',
        url: 'https://tiles.openfreemap.org/styles/liberty', // Detailed OSM Liberty style
    },
    terrain: {
        name: 'Terrain & Topography',
        url: 'https://tiles.openfreemap.org/styles/liberty', // Liberty with 3D terrain overlay
    },
    satellite: {
        name: 'Satellite View',
        url: 'https://tiles.openfreemap.org/styles/bright', // Bright style (lighter)
    },
    economic: {
        name: 'Economic Centers',
        url: '/styles/economic.json', // Custom style with temporal capital visualization
    },
};

let currentMapStyle: MapStyle = 'political';

type SceneKey = 'overview';
const mapScenes: Record<SceneKey, { title: string; description: string; center: [number, number]; zoom: number; pitch: number; bearing: number; } > = {
    overview: {
        title: 'Central Europe',
        description: 'Regional view of historical territorial changes.',
        center: [19.04, 47.5],
        zoom: 5.5,
        pitch: 45,
        bearing: 0,
    },
};

// Historical periods covering the development of capitalism
type TimePeriod = 'late-feudal' | 'early-modern' | 'mercantile' | 'early-industrial' | 'high-industrial' | 'imperial' | 'interwar' | 'cold-war';
const timePeriods: Record<TimePeriod, { year: number; label: string; description: string; dataFile: string; } > = {
    'late-feudal': { 
        year: 1450, 
        label: 'Late Feudalism', 
        description: 'Guild cities, Venetian trade dominance, Ottoman expansion begins.',
        dataFile: '1450'
    },
    'early-modern': { 
        year: 1550, 
        label: 'Early Modern', 
        description: 'Ottoman-Habsburg frontier solidifies, proto-capitalist trade routes emerge.',
        dataFile: '1550'
    },
    'mercantile': { 
        year: 1700, 
        label: 'Mercantile Era', 
        description: 'Habsburg reconquest complete, mercantilist empires, manufacturing towns grow.',
        dataFile: '1700'
    },
    'early-industrial': { 
        year: 1800, 
        label: 'Early Industrial Revolution', 
        description: 'Steam power, coalfield industrialization, rural proletarianization begins.',
        dataFile: '1800'
    },
    'high-industrial': { 
        year: 1870, 
        label: 'High Industrial Era', 
        description: 'Railway networks, Austro-Hungarian dual monarchy, mass urbanization.',
        dataFile: '1870'
    },
    'imperial': { 
        year: 1914, 
        label: 'High Imperialism', 
        description: 'Global capital flows, imperial borders peak before WWI collapse.',
        dataFile: '1914'
    },
    'interwar': { 
        year: 1938, 
        label: 'Interwar Period', 
        description: 'Treaty of Trianon reshapes borders, state capitalism, nationalist fragmentation.',
        dataFile: '1938'
    },
    'cold-war': { 
        year: 1980, 
        label: 'Cold War Division', 
        description: 'Iron Curtain divides Europe, command vs. welfare capitalism.',
        dataFile: '1980'
    },
};

let currentTimePeriod: TimePeriod = 'cold-war';

// Data layer state
let activeLayers = {
    boundaries: true,
    trade: false,
    production: false,
    urban: false,
};

// Async function to load period-specific boundary data
// TODO: Replace with Natural Earth or CShapes historical boundaries
async function loadBoundaryData(_period: TimePeriod): Promise<GeoJSON.FeatureCollection> {
    // Placeholder - will fetch from authoritative sources
    return {
        type: 'FeatureCollection',
        features: []
    };
}

// Async function to load trade route data
async function loadTradeData(): Promise<GeoJSON.FeatureCollection> {
    const response = await fetch('/data/trade/routes.geojson');
    return response.json();
}

// Async function to load railway data
async function loadRailwayData(): Promise<GeoJSON.FeatureCollection> {
    const response = await fetch('/data/trade/railways.geojson');
    return response.json();
}

// Async function to load production site data
async function loadProductionData(): Promise<GeoJSON.FeatureCollection> {
    const response = await fetch('/data/production/sites.geojson');
    return response.json();
}

// Async function to load urban/city data
async function loadUrbanData(): Promise<GeoJSON.FeatureCollection> {
    const response = await fetch('/data/urban/cities.geojson');
    return response.json();
}

// Async function to load capital concentration data for a time period
async function loadCapitalData(period: TimePeriod): Promise<GeoJSON.FeatureCollection> {
    const dataFile = timePeriods[period].dataFile;
    try {
        const response = await fetch(`/data/capital/${dataFile}.geojson`);
        if (!response.ok) {
            console.warn(`No capital data file for ${period} (${dataFile}), using empty dataset`);
            return { type: 'FeatureCollection', features: [] };
        }
        const data = await response.json();
        console.log(`Loaded capital data for ${period}:`, data.features.length, 'features');
        return data;
    } catch (err) {
        console.warn(`Error loading capital data for ${period}:`, err);
        return { type: 'FeatureCollection', features: [] };
    }
}

// Async function to load period narrative content
async function loadPeriodContent(period: TimePeriod): Promise<string> {
    const response = await fetch(`/content/${period}.md`);
    return response.text();
}

function goMapScene(sceneKey: SceneKey) {
    const target = mapScenes[sceneKey];
    if (!map || !target) return;
    map.flyTo({
        center: target.center,
        zoom: target.zoom,
        pitch: target.pitch,
        bearing: target.bearing,
        duration: 1800,
        essential: true,
    });
}

// Function to detect region based on map center
function getRegionName(lng: number, lat: number): string {
    // Simple region detection based on coordinates
    if (lat > 55) return 'Scandinavia';
    if (lat > 50 && lng < 5) return 'British Isles';
    if (lat > 50 && lng < 15) return 'Western Europe';
    if (lat > 48 && lng > 15 && lng < 30) return 'Central Europe';
    if (lat > 45 && lng > 30) return 'Eastern Europe';
    if (lat > 40 && lng > 20 && lng < 30) return 'Balkans';
    if (lat > 35 && lng < 10) return 'Iberian Peninsula';
    if (lat > 40 && lng > 5 && lng < 20) return 'Mediterranean';
    if (lat < 40 && lng > 25) return 'Eastern Mediterranean';
    if (lat < 40) return 'Southern Europe';
    return 'Europe';
}

// Function to update lesson panel region
function updateRegionPanel() {
    if (!map) return;
    const center = map.getCenter();
    const regionName = getRegionName(center.lng, center.lat);
    const lessonPanel = document.getElementById('lesson-panel');
    const heading = lessonPanel?.querySelector('h3');
    if (heading) {
        heading.textContent = regionName;
    }
}

// Function to add all data layers (called on initial load and after style changes)
function addDataLayers() {
    if (!map) return;
    
    console.log('addDataLayers called with currentMapStyle:', currentMapStyle);
    
    // Add empty sources for dynamic data loading
    if (!map.getSource('historical-boundaries')) {
        map.addSource('historical-boundaries', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    }
    if (!map.getLayer('historical-boundaries-fill')) {
        map.addLayer({
            id: 'historical-boundaries-fill',
            type: 'fill',
            source: 'historical-boundaries',
            paint: {
                'fill-color': '#ff6b6b',
                'fill-opacity': 0.3,
            },
        });
    }
    if (!map.getLayer('historical-boundaries-line')) {
        map.addLayer({
            id: 'historical-boundaries-line',
            type: 'line',
            source: 'historical-boundaries',
            paint: {
                'line-color': '#ff4757',
                'line-width': 2,
            },
        });
    }

    // Economic/Capital concentration layer
    if (!map.getSource('capital-centers')) {
        map.addSource('capital-centers', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    }
    
    // Background economic zone coloring - large diffuse circles to tint the base map
    if (!map.getLayer('economic-zones')) {
        map.addLayer({
            id: 'economic-zones',
            type: 'circle',
            source: 'capital-centers',
            layout: { visibility: currentMapStyle === 'economic' ? 'visible' : 'none' },
            paint: {
                'circle-radius': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    0, 100,
                    9, 200
                ],
                'circle-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'economic_weight'],
                    0, '#0a0a0a',  // Periphery - nearly invisible on black background
                    2, '#3a2a0a',  // Extractive zones - dark brown
                    4, '#6a4a0a',  // Secondary extraction - brown
                    6, '#aa8800',  // Emerging accumulation - gold/yellow
                    8, '#ff6600',  // Major centers - orange
                    10, '#ff0000'  // Core capital accumulation - bright red
                ],
                'circle-blur': 1,
                'circle-opacity': [
                    'interpolate',
                    ['linear'],
                    ['get', 'economic_weight'],
                    0, 0.05,
                    10, 0.15
                ],
            },
        });
    }
    
    // Heatmap layer for capital concentration
    map.addLayer({
        id: 'capital-heatmap',
        type: 'heatmap',
        source: 'capital-centers',
        layout: { visibility: currentMapStyle === 'economic' ? 'visible' : 'none' },
        paint: {
            'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'economic_weight'],
                0, 0,
                10, 1
            ],
            'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 0.4,
                9, 1
            ],
            'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(10,10,10,0)',       // Transparent black
                0.2, 'rgba(58,42,10,0.2)',   // Dark brown (extraction)
                0.4, 'rgba(170,136,0,0.4)',  // Gold/yellow (accumulation emerging)
                0.6, 'rgba(255,136,0,0.6)',  // Orange (major centers)
                0.8, 'rgba(255,68,0,0.8)',   // Red-orange (intense accumulation)
                1, 'rgba(255,0,0,0.9)'       // Bright red (peak capital concentration)
            ],
            'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 50,
                9, 120
            ],
            'heatmap-opacity': 0.6,
        },
    });
    
    // Capital center labels - only cities with real capital accumulation
    map.addLayer({
        id: 'capital-labels',
        type: 'symbol',
        source: 'capital-centers',
        layout: {
            visibility: currentMapStyle === 'economic' ? 'visible' : 'none',
            'text-field': ['get', 'name'],
            'text-size': [
                'interpolate',
                ['linear'],
                ['get', 'economic_weight'],
                0, 11,
                10, 20
            ],
            'text-offset': [0, 1],
            'text-anchor': 'top',
            'text-allow-overlap': false,
            'text-optional': false
        },
        paint: {
            'text-color': '#ffffff',
            'text-halo-color': '#000000',
            'text-halo-width': 2.5,
            'text-halo-blur': 0.5,
            'text-opacity': 1
        },
    });
    
    // Capital center markers - small dots to mark centers
    if (!map.getLayer('capital-markers')) {
        map.addLayer({
            id: 'capital-markers',
            type: 'circle',
            source: 'capital-centers',
            layout: { visibility: currentMapStyle === 'economic' ? 'visible' : 'none' },
            paint: {
                'circle-radius': [
                    'interpolate',
                    ['linear'],
                    ['get', 'economic_weight'],
                    0, 2,
                    10, 5
                ],
                'circle-color': '#ffffff',
                'circle-stroke-color': '#000000',
                'circle-stroke-width': 1,
                'circle-opacity': 0.9
            },
        });
    }
    
    console.log('Added capital heatmap layer with visibility:', currentMapStyle === 'economic' ? 'visible' : 'none');
}

// Initialize MapLibre (default view)
map = new maplibregl.Map({
    container: mapContainer,
    style: mapStyles[currentMapStyle].url,
    center: mapScenes.overview.center,
    zoom: mapScenes.overview.zoom,
    pitch: mapScenes.overview.pitch,
    bearing: mapScenes.overview.bearing,
    hash: false,
    pitchWithRotate: true, // Enable 3D rotation
    dragRotate: true, // Enable rotation with right-click drag
});

map.addControl(new maplibregl.NavigationControl({ 
    visualizePitch: true,
    showCompass: true,
    showZoom: true
}), 'top-left');

map.on('load', () => {
    // Note: Terrain source removed due to CORS errors
    // If needed in future, would require different tile source
    
    // Add all data layers
    addDataLayers();

    // Update region name on map move - disabled due to render loop errors
    // map.on('moveend', updateRegionPanel);

    // Initialize legend
    updateLegend();

    goMapScene('overview');
    
    // Load initial capital data for economic mode
    loadCapitalData('cold-war').then(capitalData => {
        (map.getSource('capital-centers') as maplibregl.GeoJSONSource)?.setData(capitalData);
    });
});

// Lesson overlay (for text/annotations)
const lessonPanel = document.createElement('div');
lessonPanel.id = 'lesson-panel';
lessonPanel.innerHTML = `
    <h3>${mapScenes.overview.title}</h3>
    <p>${mapScenes.overview.description}</p>
`;
document.body.appendChild(lessonPanel);

// Map Legend (bottom left) - hidden for now
const mapLegend = document.createElement('div');
mapLegend.id = 'map-legend';
mapLegend.style.display = 'none';
document.body.appendChild(mapLegend);

// Function to update legend - simplified
function updateLegend() {
    // Disabled for now
}

// Map Style Switcher (top)
const styleControls = document.createElement('div');
styleControls.id = 'style-controls';
styleControls.innerHTML = `
    <button data-style="political" class="style-btn active">Political</button>
    <button data-style="terrain" class="style-btn">Terrain</button>
    <button data-style="satellite" class="style-btn">Satellite</button>
    <button data-style="economic" class="style-btn">Economic</button>
`;
document.body.appendChild(styleControls);

// Time Controls (bottom right)
const timeControls = document.createElement('div');
timeControls.id = 'time-controls';
timeControls.innerHTML = `
    <div class="time-slider-container">
        <label for="time-slider">Historical Timeline (1450-1980)</label>
        <input type="range" id="time-slider" min="0" max="7" value="7" step="1">
        <div class="time-labels">
            <span>1450</span>
            <span>1550</span>
            <span>1700</span>
            <span>1800</span>
            <span>1870</span>
            <span>1914</span>
            <span>1938</span>
            <span>1980</span>
        </div>
    </div>
    <div id="time-description"></div>
    <div class="layer-toggles">
        <label><input type="checkbox" id="layer-boundaries" checked> Historical Boundaries</label>
    </div>
`;
document.body.appendChild(timeControls);

// Map style button handlers
document.querySelectorAll('.style-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        const target = e.target as HTMLButtonElement;
        const style = target.dataset.style as MapStyle;
        
        if (style === currentMapStyle || !map) return;
        
        // Update active state
        document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
        target.classList.add('active');
        
        // Store current state before style switch
        const center = map.getCenter();
        const zoom = map.getZoom();
        const pitch = map.getPitch();
        const bearing = map.getBearing();
        
        currentMapStyle = style;
        
        console.log('Switching to style:', style);
        
        // Hide map during transition to economic mode to avoid flash of unstyled content
        if (style === 'economic') {
            mapContainer.style.opacity = '0';
        }
        
        // Switch the map style
        map.setStyle(mapStyles[style].url);
        
        // Re-add sources and layers after style loads
        // Using 'idle' event which fires when style is fully loaded
        const handleStyleLoaded = () => {
            console.log('Style loaded (idle event), currentMapStyle is:', currentMapStyle);
            
            // Remove this handler so it doesn't fire again
            map.off('idle', handleStyleLoaded);
            
            // Restore camera position
            map.jumpTo({ center, zoom, pitch, bearing });
            
            // Re-add all data layers (they will get correct visibility from currentMapStyle)
            addDataLayers();
            
            // Note: Style customizations now handled by custom style JSON for economic mode
            
            // Show map after customizations applied
            if (style === 'economic') {
                setTimeout(() => {
                    mapContainer.style.opacity = '1';
                }, 100);
            } else {
                mapContainer.style.opacity = '1';
            }
            
            // Reload current period data
            loadAndUpdatePeriod(currentTimePeriod);
            
            // For economic mode, load capital data
            if (style === 'economic') {
                loadCapitalData(currentTimePeriod).then(capitalData => {
                    console.log('Loading capital data on style switch:', capitalData);
                    (map.getSource('capital-centers') as maplibregl.GeoJSONSource)?.setData(capitalData);
                });
            }
            
            // Update legend for new style
            updateLegend();
        };
        
        // Attach the handler
        map.on('idle', handleStyleLoaded);
    });
});

// Time slider handler
const timeSlider = document.getElementById('time-slider') as HTMLInputElement;
const timeDescription = document.getElementById('time-description') as HTMLDivElement;

async function loadAndUpdatePeriod(period: TimePeriod) {
    currentTimePeriod = period;
    const periodData = timePeriods[period];
    
    if (!map) return;
    
    // Update time description
    timeDescription.textContent = `${periodData.label}: ${periodData.description}`;
    
    // Load and update boundary data
    if (activeLayers.boundaries && map.getSource('historical-boundaries')) {
        const boundaryData = await loadBoundaryData(period);
        (map.getSource('historical-boundaries') as maplibregl.GeoJSONSource).setData(boundaryData);
    }
    
    // Update capital concentration heatmap for all modes (but only visible in economic)
    const capitalData = await loadCapitalData(period);
    const capitalSource = map.getSource('capital-centers');
    if (capitalSource) {
        (capitalSource as maplibregl.GeoJSONSource).setData(capitalData);
    }
    
    // Load and display period narrative content
    const content = await loadPeriodContent(period);
    updateLessonPanelWithMarkdown(content);
}

function updateLessonPanelWithMarkdown(markdown: string) {
    const lessonPanel = document.getElementById('lesson-panel');
    if (!lessonPanel) return;
    
    // Simple markdown-to-HTML conversion
    const html = markdown
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    lessonPanel.innerHTML = `<div class="lesson-content"><p>${html}</p></div>`;
}

timeSlider.addEventListener('input', (e) => {
    const value = parseInt((e.target as HTMLInputElement).value);
    const periods: TimePeriod[] = ['late-feudal', 'early-modern', 'mercantile', 'early-industrial', 'high-industrial', 'imperial', 'interwar', 'cold-war'];
    loadAndUpdatePeriod(periods[value]);
});

// Layer toggle handlers
document.getElementById('layer-boundaries')?.addEventListener('change ', (e) => {
    const checked = (e.target as HTMLInputElement).checked;
    activeLayers.boundaries = checked;
    map?.setLayoutProperty('historical-boundaries-fill', 'visibility', checked ? 'visible' : 'none');
    map?.setLayoutProperty('historical-boundaries-line', 'visibility', checked ? 'visible' : 'none');
    updateLegend();
});

// Initialize with default period
loadAndUpdatePeriod('cold-war');

// Handle window resize
window.addEventListener('resize', () => {
    map?.resize();
});