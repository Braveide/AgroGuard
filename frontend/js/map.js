import { showToast, spinner, errorBox, sanitize, badgeRiesgo } from "./utils.js";

export function inicializarMapa(lat = 19.4326, lng = -99.1332) {
  // Remove previous map instance if any
  if (window.mapaLeaflet) {
    window.mapaLeaflet.remove();
    window.mapaLeaflet = null;
  }
  // Ensure the map container matches its wrapper height
  const wrapper = document.getElementById('mapa-wrapper');
  const mapaDiv = document.getElementById('mapa');
  if (wrapper && mapaDiv) {
    mapaDiv.style.height = wrapper.offsetHeight + 'px';
  }
  const mapa = L.map('mapa', { zoomControl: true }).setView([lat, lng], 5);
  window.mapaLeaflet = mapa;
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(mapa);
  setTimeout(() => mapa && mapa.invalidateSize(), 200);
  return mapa;
}

export async function cargarMapa() {
// Access global API configuration
const API_BASE = globalThis.API_BASE;
const API_KEY = globalThis.API_KEY;
  const status = document.getElementById('mapa-status');
  if (!status) return;
  status.textContent = 'Cargando focos...';
  const mapa = inicializarMapa();
  try {
    const res = await fetch(`${API_BASE}/focos`, {
      headers: { 'x-api-key': API_KEY },
    });
    if (!res.ok) { status.textContent = 'No hay registros con ubicación aún.'; return; }
    const focos = await res.json();
    if (!Array.isArray(focos) || !focos.length) { status.textContent = 'No hay focos con ubicación registrada aún.'; return; }
    const colores = { Alto: '#c0392b', Medio: '#d4821a', Bajo: '#3d5a2a' };
    const bounds = [];
    focos.forEach(f => {
      const color = colores[f.riesgo] || '#555';
      L.circleMarker([f.latitud, f.longitud], {
        radius: 10,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85,
      }).addTo(mapa).bindPopup(`
        <div style="font-family:sans-serif;min-width:180px;">
          <p style="font-weight:700;margin:0 0 4px;color:var(--white);">${sanitize(f.nombre_plaga)}</p>
          <p style="font-style:italic;font-size:.8rem;margin:0 0 6px;color:var(--muted);">${sanitize(f.nombre_cientifico)}</p>
          <p style="font-size:.75rem;margin:0;"><b>Riesgo:</b> ${sanitize(f.riesgo)}</p>
          <p style="font-size:.75rem;margin:0;"><b>Familia:</b> ${sanitize(f.familia)}</p>
          <p style="font-size:.75rem;margin:2px 0 0;color:var(--muted);">${sanitize(f.fecha)}</p>
        </div>`);
      bounds.push([f.latitud, f.longitud]);
    });
    if (bounds.length) mapa.fitBounds(bounds, { padding: [40, 40] });
    status.textContent = `${focos.length} foco(s) mostrado(s) en el mapa.`;
  } catch (err) {
    status.textContent = 'No se pudo conectar con el servidor.';
  }
}
