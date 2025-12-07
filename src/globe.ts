23// Globe view - Three.js 3D globe with texture swapping
// Extracted for future use - can be re-integrated as a separate page/module

import './style.css'
import * as three from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GUI } from 'three/examples/jsm/libs/lil-gui.module.min.js';

// Scene setup
const scene = new three.Scene();
scene.background = new three.Color(0x1a1a2e);
const camera = new three.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.01, 1000);
const renderer = new three.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// OrbitControls setup
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 1.05;
controls.maxDistance = 10;

// Lighting
const ambientLight = new three.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const directionalLight = new three.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(5, 10, 7.5);
scene.add(directionalLight);

// Create Globe
const globeGeometry = new three.SphereGeometry(1, 64, 64);
const textureLoader = new three.TextureLoader();

// Texture URLs for different views
const textures = {
    political: '/assets/views/earth-political.jpg',
    geographic: '/assets/views/earth-blue-marble.jpg',
    nightlights: '/assets/views/earth-night.jpg',
    topology: '/assets/views/earth-topology.jpg',
};

let currentTexture: keyof typeof textures = 'political';
const globeMaterial = new three.MeshPhongMaterial({
    map: textureLoader.load(textures[currentTexture]),
    bumpScale: 0.02,
    shininess: 5,
});

const globe = new three.Mesh(globeGeometry, globeMaterial);
scene.add(globe);

const devParams = {
    globeRotationSpeed: 0.001,
    globeScale: 1.0,
    globePositionX: 0,
    globePositionY: 0,
    globePositionZ: 0,
    ambientLightIntensity: 0.6,
    directionalLightIntensity: 0.8,
    cameraFOV: 75,
    autoRotate: true,
};

// Function to switch globe textures
function switchGlobeView(viewType: keyof typeof textures) {
    currentTexture = viewType;
    textureLoader.load(textures[viewType], (texture) => {
        globeMaterial.map = texture;
        globeMaterial.needsUpdate = true;
    });
    console.log(`Switched to ${viewType} view`);
}

// Keyboard controls to switch views
window.addEventListener('keydown', (e) => {
    switch(e.key) {
        case '1':
            switchGlobeView('political');
            break;
        case '2':
            switchGlobeView('geographic');
            break;
        case '3':
            switchGlobeView('nightlights');
            break;
        case '4':
            switchGlobeView('topology');
            break;
    }
});

// Camera position
camera.position.set(0, 0, 2.5);

// Developer Controls
const gui = new GUI();
gui.domElement.style.position = 'absolute';
gui.domElement.style.top = '10px';
gui.domElement.style.left = '10px';
gui.title('Dev Controls');

const globeFolder = gui.addFolder('Globe');
globeFolder.add(devParams, 'globeRotationSpeed', 0, 0.01).name('Rotation Speed');
globeFolder.add(devParams, 'globeScale', 0.5, 2).onChange((v: number) => {
    globe.scale.set(v, v, v);
}).name('Scale');
globeFolder.add(devParams, 'globePositionX', -2, 2).onChange((v: number) => {
    globe.position.x = v;
}).name('Position X');
globeFolder.add(devParams, 'globePositionY', -2, 2).onChange((v: number) => {
    globe.position.y = v;
}).name('Position Y');
globeFolder.add(devParams, 'globePositionZ', -2, 2).onChange((v: number) => {
    globe.position.z = v;
}).name('Position Z');
globeFolder.add(devParams, 'autoRotate').name('Auto Rotate');

const lightFolder = gui.addFolder('Lighting');
lightFolder.add(devParams, 'ambientLightIntensity', 0, 2).onChange((v: number) => {
    ambientLight.intensity = v;
}).name('Ambient');
lightFolder.add(devParams, 'directionalLightIntensity', 0, 2).onChange((v: number) => {
    directionalLight.intensity = v;
}).name('Directional');

const cameraFolder = gui.addFolder('Camera');
cameraFolder.add(devParams, 'cameraFOV', 30, 120).onChange((v: number) => {
    camera.fov = v;
    camera.updateProjectionMatrix();
}).name('FOV');

// User Controls (bottom)
const viewControls = document.createElement('div');
viewControls.id = 'view-controls';
viewControls.innerHTML = `
    <button data-view="political" class="view-btn active">Political Boundaries</button>
    <button data-view="geographic" class="view-btn">Geographic/Terrain</button>
    <button data-view="nightlights" class="view-btn">Night Lights</button>
    <button data-view="topology" class="view-btn">Topography</button>
`;
document.body.appendChild(viewControls);

// View button handlers
document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const target = e.target as HTMLButtonElement;
        const view = target.dataset.view as keyof typeof textures;
        
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        target.classList.add('active');
        
        switchGlobeView(view);
    });
});

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    
    if (devParams.autoRotate) {
        globe.rotation.y += devParams.globeRotationSpeed;
    }
    
    controls.update();
    renderer.render(scene, camera);
}
animate();

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
