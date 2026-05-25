import { showToast } from "./utils.js";
// Access global API configuration
const API_BASE = globalThis.API_BASE;
const API_KEY = globalThis.API_KEY;
import { cargarMapa } from "./map.js";

// Accessibility and field helpers
let modoCampoActivo = false;
let reconocimientoVoz = null;
window.lectorActivo = false;
let filtroActual = 'normal';

export function toggleModoCampo() {
  modoCampoActivo = !modoCampoActivo;
  const overlay = document.getElementById('modo-campo-overlay');
  const btn = document.getElementById('btn-campo');
  if (modoCampoActivo) {
    overlay.classList.remove('hidden');
    btn.style.background = 'rgba(168,255,62,.2)';
    btn.style.borderColor = 'rgba(168,255,62,.5)';
    document.body.style.overflow = 'hidden';
  } else {
    overlay.classList.add('hidden');
    btn.style.background = 'rgba(255,255,255,.08)';
    btn.style.borderColor = 'rgba(255,255,255,.18)';
    document.body.style.overflow = '';
    document.getElementById('campo-resultado').classList.add('hidden');
    document.getElementById('campo-voz-estado').classList.add('hidden');
    detenerVoz();
  }
}

export function activarCamaraCampo() {
  document.getElementById('campo-input-imagen').click();
}

let archivoImagen = null;

function cargarPreview(file) {
  if (file.size > 5 * 1024 * 1024) {
    showToast('La imagen no debe superar 5MB.', 'error');
    return;
  }
  archivoImagen = file;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('img-preview').src = e.target.result;
    document.getElementById('img-nombre').textContent = file.name;
    document.getElementById('img-preview-wrap').classList.remove('hidden');
    document.getElementById('img-resultado').textContent = '';
  };
  reader.readAsDataURL(file);
}

export function procesarImagenCampo(event) {
  const file = event.target.files[0];
  if (!file) return;
  cargarPreview(file);
}

export async function iniciarRegistroVoz() {
  if (!('webkitSpeechRecognition' in globalThis) && !('SpeechRecognition' in globalThis)) {
    showToast('Tu navegador no soporta reconocimiento de voz.', 'error');
    return;
  }
  const voiceStateEl = document.getElementById('campo-voz-estado');
  if (voiceStateEl) voiceStateEl.classList.remove('hidden');
  const SR = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition;
  reconocimientoVoz = new SR();
  reconocimientoVoz.lang = globalThis._vozLang || 'es-MX';
  reconocimientoVoz.interimResults = true;
  reconocimientoVoz.onresult = e => {
    const t = e.results[0][0].transcript;
    document.getElementById('campo-voz-texto').textContent = '""';
    if (e.results[0].isFinal) {
      detenerVoz();
      fetch(`${API_BASE}/buscar_externo/${encodeURIComponent(t)}`, { headers: { 'x-api-key': API_KEY } })
        .then(r => { if (!r.ok) throw new Error(); return r.json(); })
        .then(g => {
          const resultado = document.getElementById('campo-resultado');
          if (resultado) resultado.classList.remove('hidden');
          const contenido = document.getElementById('campo-resultado-contenido');
          if (contenido) {
            contenido.innerHTML = `
              <p style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:var(--neon);margin-bottom:.3rem;">${sanitize(g.nombre_cientifico)}</p>
              <p style="font-family:'Manrope',sans-serif;font-size:.9rem;color:var(--muted);">Familia: ${sanitize(g.familia)} · Reino: ${sanitize(g.reino)}</p>`;
          }
        })
        .catch(() => showToast('No se encontró información.', 'error'));
    }
  };
  reconocimientoVoz.onerror = () => { detenerVoz(); showToast('Error de micrófono.', 'error'); };
  reconocimientoVoz.start();
}

export function detenerVoz() {
  if (reconocimientoVoz) { reconocimientoVoz.stop(); reconocimientoVoz = null; }
  const voiceStateEl = document.getElementById('campo-voz-estado');
  if (voiceStateEl) voiceStateEl.classList.add('hidden');
}

export function toggleDaltonismo() {
  const panel = document.getElementById('panel-accesibilidad');
  panel.classList.toggle('hidden');
}

export function aplicarFiltro(tipo) {
  document.body.classList.remove('daltonismo-protanopia','daltonismo-deuteranopia','daltonismo-tritanopia','daltonismo-achromatopsia');
  document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('activo'));
  filtroActual = tipo;
  if (tipo !== 'normal') document.body.classList.add(`daltonismo-${tipo}`);
  const btn = document.getElementById(`f-${tipo}`);
  if (btn) btn.classList.add('activo');
  const nombres = { normal: 'Sin filtro', protanopia: 'Protanopia', deuteranopia: 'Deuteranopia', tritanopia: 'Tritanopia', achromatopsia: 'Acromatopsia' };
  showToast(`🌓 Modo: ${nombres[tipo]}`, 'success');
}

export function toggleLectorVoz() {
  window.lectorActivo = !window.lectorActivo;
  const btn = document.getElementById('btn-voz');
  if (window.lectorActivo) {
    document.body.classList.add('lector-activo');
    btn.style.background = 'rgba(184,244,88,.15)';
    btn.style.borderColor = 'rgba(184,244,88,.4)';
    btn.textContent = '🛑';
    showToast('🔊 Lector de voz activado — hover para escuchar', 'success');
    document.querySelectorAll('p, h1, h2, td, label, button, a, .section-title').forEach(el => {
      el.addEventListener('mouseenter', leerElemento);
    });
  } else {
    document.body.classList.remove('lector-activo');
    btn.style.background = 'rgba(255,255,255,.08)';
    btn.style.borderColor = 'rgba(255,255,255,.18)';
    btn.textContent = '🔊';
    showToast('🛑 Lector de voz desactivado', 'success');
    speechSynthesis.cancel();
    document.querySelectorAll('p, h1, h2, td, label, button, a, .section-title').forEach(el => {
      el.removeEventListener('mouseenter', leerElemento);
    });
  }
}

export function leerElemento(e) {
  const texto = e.currentTarget.innerText?.trim();
  if (!texto || texto.length < 2) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(texto);
  utterance.lang = globalThis._vozLang || 'es-MX';
  utterance.rate = 0.95;
  utterance.pitch = 1;
  speechSynthesis.speak(utterance);
}

export function obtenerUbicacion() {
  const status = document.getElementById('geo-status');
  if (!navigator.geolocation) {
    status.textContent = '⚠️ Tu navegador no soporta geolocalización.'; return;
  }
  status.textContent = '📍 Detectando ubicación...';
  navigator.geolocation.getCurrentPosition(
    pos => {
      document.getElementById('f-latitud').value = pos.coords.latitude.toFixed(6);
      document.getElementById('f-longitud').value = pos.coords.longitude.toFixed(6);
      status.textContent = `✔️ Ubicación detectada (precisión: ${Math.round(pos.coords.accuracy)}m)`;
    },
    err => { status.textContent = `⚠️ Error: ${err.message}`; },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

export function verMapaCampo() {
  toggleModoCampo();
  if (window.cambiarTab) window.cambiarTab('mapa');
  setTimeout(() => {
    if (cargarMapa) cargarMapa();
  }, 300);
}
