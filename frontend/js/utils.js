// Utility UI helper functions
export function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => { t.className = ''; }, 3200);
}

export function badgeRiesgo(riesgo) {
  const map = { Alto: 'badge-alto', Medio: 'badge-medio', Bajo: 'badge-bajo' };
  return `<span class="badge ${map[riesgo] || ''}">${riesgo || '—'}</span>`;
}

export function spinner() {
  return `<div class="flex justify-center py-4"><div class="spinner"></div></div>`;
}

export function errorBox(msg) {
  return `
    <div class="rounded-lg p-3 text-sm fade-up" style="background:rgba(255,71,87,.08);color:var(--red);border:1px solid rgba(255,71,87,.3);">
      <span style="font-weight:600;">⚠️ Sin datos</span><br/>
      <span style="opacity:.85;">${msg || ''}</span>
    </div>`;
}

export function sanitize(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function isValidHttpUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}
