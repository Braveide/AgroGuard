import { showToast, badgeRiesgo, spinner, errorBox, sanitize } from "./utils.js";

// Access global API configuration
const API_BASE = globalThis.API_BASE;
const API_KEY = globalThis.API_KEY;

// Register a new plaga
export async function registrarPlaga() {
  const nombre = document.getElementById('f-nombre').value.trim();
  const nombre_cientifico = document.getElementById('f-nombre-cientifico').value.trim();
  const familia = document.getElementById('f-familia').value.trim();
  const reino = document.getElementById('f-reino').value.trim();
  const riesgo = document.getElementById('f-riesgo').value;
  const ficha_tecnica = document.getElementById('f-ficha').value.trim();
  const fecha = document.getElementById('f-fecha').value;

  if (!nombre || !nombre_cientifico || !familia || !reino || !riesgo || !ficha_tecnica || !fecha) {
    showToast('Completa todos los campos antes de guardar.', 'error');
    return;
  }

  try {
    const latVal = document.getElementById('f-latitud').value;
    const lngVal = document.getElementById('f-longitud').value;
    const res = await fetch(`${API_BASE}/registrar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
      },
      body: JSON.stringify({
        nombre_plaga: nombre,
        nombre_cientifico,
        familia,
        reino,
        riesgo,
        ficha_tecnica,
        fecha,
        latitud: latVal ? Number.parseFloat(latVal) : null,
        longitud: lngVal ? Number.parseFloat(lngVal) : null,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error desconocido');
    }
    const data = await res.json();
    showToast(`✔️ Plaga #${data.id} registrada correctamente.`, 'success');
    ['f-nombre','f-nombre-cientifico','f-familia','f-reino','f-ficha'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    document.getElementById('f-riesgo').value = '';
    document.getElementById('f-fecha').value = new Date().toISOString().slice(0,10);
    document.getElementById('geo-status').textContent = '';
  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
  }
}

// Perform an integrated search (local + GBIF)
export async function buscarIntegral() {
  const nombre = document.getElementById('inp-buscar').value.trim();
  if (!nombre) { showToast('Escribe un nombre para buscar.', 'error'); return; }

  document.getElementById('resultados').classList.remove('hidden');
  document.getElementById('local-content').innerHTML = spinner();
  document.getElementById('gbif-content').innerHTML = spinner();

  const [localResult, gbifResult] = await Promise.allSettled([
    fetch(`${API_BASE}/buscar_local/${encodeURIComponent(nombre)}`, { headers: { 'x-api-key': API_KEY } })
      .then(async r => {
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'No encontrado'); }
        return r.json();
      }),
    fetch(`${API_BASE}/buscar_externo/${encodeURIComponent(nombre)}`, { headers: { 'x-api-key': API_KEY } })
      .then(async r => {
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'No encontrado'); }
        return r.json();
      })
  ]);

  // Render local results
  if (localResult.status === 'fulfilled') {
    const registros = localResult.value;
    if (!Array.isArray(registros)) {
      document.getElementById('local-content').innerHTML = errorBox('Respuesta inesperada del servidor.');
    } else {
      document.getElementById('local-content').innerHTML = registros.map(r => `
        <div class="card p-4 fade-up" style="border-left:3px solid var(--cyan);background:rgba(5,20,28,.8);">
          <p class="mono text-xs mb-2" style="color:var(--cyan);">REGISTRO LOCAL</p>
          <dl style="font-size:.85rem;">
            <div class="res-row"><dt>Nombre</dt><dd style="font-weight:600;color:var(--text);">${sanitize(r.nombre_plaga)}</dd></div>
            <div class="res-row"><dt>Nombre científico</dt><dd style="font-style:italic;font-weight:600;color:var(--text);">${sanitize(r.nombre_cientifico)}</dd></div>
            <div class="res-row"><dt>Familia</dt><dd style="color:var(--text);">${sanitize(r.familia)}</dd></div>
            <div class="res-row"><dt>Reino</dt><dd style="color:var(--text);">${sanitize(r.reino)}</dd></div>
            <div class="res-row"><dt>Riesgo</dt><dd>${badgeRiesgo(r.riesgo)}</dd></div>
            <div class="res-row res-row--stack"><dt>Ficha técnica</dt><dd style="color:var(--text);">${sanitize(r.ficha_tecnica)}</dd></div>
          </dl>
          <p class="mono text-right mt-2" style="font-size:.65rem;color:var(--muted);">fuente: BD local · #${sanitize(r.id)} · ${sanitize(r.fecha)}</p>
        </div>`).join('');
    }
  } else {
    document.getElementById('local-content').innerHTML = errorBox(localResult.reason?.message || 'Sin registros locales.');
  }

  // Render GBIF results
  if (gbifResult.status === 'fulfilled') {
    const g = gbifResult.value;
    document.getElementById('gbif-content').innerHTML = `
      <div class="card p-4 fade-up" style="border-left:3px solid var(--neon);background:rgba(10,26,14,.8);">
        ${g.foto_url ? `
        <div style="margin:-1rem -1rem 0.75rem -1rem;border-radius:.75rem .75rem 0 0;overflow:hidden;height:160px;">
          <img src="${sanitize(g.foto_url)}" alt="Foto de la especie"
               style="width:100%;height:100%;object-fit:cover;display:block;"
               onerror="this.parentElement.style.display='none'" />
        </div>` : ''}
        <p class="mono text-xs mb-2" style="color:var(--neon);">CLASIFICACIÓN TAXONÓMICA</p>
        <dl style="font-size:.85rem;">
          <div class="res-row"><dt>Nombre científico</dt><dd style="font-style:italic;font-weight:600;color:var(--text);">${sanitize(g.nombre_cientifico)}</dd></div>
          <div class="res-row"><dt>Familia</dt><dd style="color:var(--text);">${sanitize(g.familia)}</dd></div>
          <div class="res-row"><dt>Reino</dt><dd style="color:var(--text);">${sanitize(g.reino)}</dd></div>
          ${g.confianza != null ? `
          <div class="res-row" style="align-items:center;">
            <dt>Confianza</dt>
            <dd>
              <div style="display:flex;align-items:center;gap:.5rem;">
                <div style="flex:1;height:6px;background:rgba(255,255,255,.1);border-radius:999px;min-width:60px;">
                  <div style="width:${sanitize(g.confianza)}%;height:100%;background:var(--neon);border-radius:999px;"></div>
                </div>
                <span class="mono" style="font-size:.75rem;white-space:nowrap;">${sanitize(g.confianza)}%</span>
              </div>
            </dd>
          </div>` : ''}
          ${g.wikipedia_url ? `
          <div class="res-row">
            <dt>Wikipedia</dt>
            <dd><a href="${sanitize(g.wikipedia_url)}" target="_blank" rel="noopener"
                  style="color:var(--cyan);font-size:.82rem;text-decoration:none;display:inline-flex;align-items:center;gap:.3rem;">
              📖 Ver artículo completo
            </a></dd>
          </div>` : ''}
        </dl>
        <p class="mono text-right mt-2" style="font-size:.65rem;color:var(--muted);">fuente: GBIF.org + iNaturalist</p>
      </div>`;
  } else {
    document.getElementById('gbif-content').innerHTML = errorBox(gbifResult.reason?.message || 'GBIF no devolvió resultados.');
  }
}
