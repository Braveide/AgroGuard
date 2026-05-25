// Core configuration constants
const API = "https://agroguard-03nz.onrender.com";
const API_KEY = "my-public-key";
const API_BASE = API;

// Global map reference (used by map module)
globalThis.mapaLeaflet = null;
let mapaLeaflet = null; // alias for convenience; not exported directly

// ResizeObserver: keep map container height in sync with its wrapper
window.addEventListener('DOMContentLoaded', () => {
  const wrapper = document.getElementById('mapa-wrapper');
  if (wrapper && globalThis.ResizeObserver) {
    new ResizeObserver(() => {
      const mapaDiv = document.getElementById('mapa');
      if (mapaDiv && wrapper.offsetHeight > 0) {
        mapaDiv.style.height = wrapper.offsetHeight + 'px';
      }
      if (globalThis.mapaLeaflet) globalThis.mapaLeaflet.invalidateSize();
    }).observe(wrapper);
  }
});

// Import all functional modules
import "./utils.js"; // Ensure utils are loaded (functions exported are used by other modules)
import { cambiarTab } from "./ui.js";
import { registrarPlaga, buscarIntegral } from "./api.js";
import { cambiarIdioma, i18n } from "./i18n.js";
import { toggleModoCampo, activarCamaraCampo, procesarImagenCampo, iniciarRegistroVoz, detenerVoz, toggleDaltonismo, aplicarFiltro, toggleLectorVoz, leerElemento, obtenerUbicacion, verMapaCampo } from "./a11y.js";
import { inicializarMapa, cargarMapa } from "./map.js";

// Expose functions needed by HTML inline event handlers
window.cambiarTab = cambiarTab;
window.registrarPlaga = registrarPlaga;
window.buscarIntegral = buscarIntegral;
window.cambiarIdioma = cambiarIdioma;
window.toggleModoCampo = toggleModoCampo;
window.activarCamaraCampo = activarCamaraCampo;
window.procesarImagenCampo = procesarImagenCampo;
window.iniciarRegistroVoz = iniciarRegistroVoz;
window.detenerVoz = detenerVoz;
window.toggleDaltonismo = toggleDaltonismo;
window.aplicarFiltro = aplicarFiltro;
window.toggleLectorVoz = toggleLectorVoz;
window.leerElemento = leerElemento;
window.obtenerUbicacion = obtenerUbicacion;
window.verMapaCampo = verMapaCampo;
window.inicializarMapa = inicializarMapa;
window.cargarMapa = cargarMapa;

// Additional UI initialization after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Search input: trigger search on Enter key
  const buscarInput = document.getElementById('inp-buscar');
  if (buscarInput) {
    buscarInput.addEventListener('keydown', e => { if (e.key === 'Enter') buscarIntegral(); });
  }
  // Initialize map and ensure proper sizing
  inicializarMapa();
  setTimeout(() => { if (window.mapaLeaflet) window.mapaLeaflet.invalidateSize(); }, 300);
  // Set default date for registration form
  const fechaInput = document.getElementById('f-fecha');
  if (fechaInput) fechaInput.value = new Date().toISOString().slice(0, 10);
});
