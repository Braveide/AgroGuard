// UI navigation helpers
export function cambiarTab(tab) {
  // Hide all panels and deactivate all tabs
  ['consultar','imagen','registrar','mapa'].forEach(t => {
    const panel = document.getElementById(`panel-${t}`);
    const tabBtn = document.getElementById(`tab-${t}`);
    if (panel) panel.classList.add('hidden');
    if (tabBtn) tabBtn.classList.remove('active-tab');
  });
  // Show requested panel and activate its tab
  const panelActual = document.getElementById(`panel-${tab}`);
  const tabActual = document.getElementById(`tab-${tab}`);
  if (panelActual) panelActual.classList.remove('hidden');
  if (tabActual) tabActual.classList.add('active-tab');
  // If map tab, load/refresh map
  if (tab === 'mapa') {
    setTimeout(() => {
      if (window.mapaLeaflet) {
        window.mapaLeaflet.invalidateSize();
      } else {
        // cargarMapa will be attached to window in bootstrap
        if (window.cargarMapa) window.cargarMapa();
      }
    }, 150);
  }
}
