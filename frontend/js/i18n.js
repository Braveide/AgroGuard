import { showToast } from "./utils.js";

// Internationalization dictionaries
export const i18n = {
  es: {
    subtitulo:        'SISTEMA DE GESTIÓN DE PLAGAS · v1.0',
    btn_pdf:          'REPORTE PDF',
    tab_consultar:    'Consultar',
    tab_imagen:       'Imagen',
    tab_registrar:    'Registrar',
    tab_mapa:         "Mapa",
    titulo_consultar: '<span data-i18n="titulo_consultar">Consulta Integral de Plaga</span>',
    desc_consultar:   'Ingresa un nombre y obtendrás simultáneamente los registros locales y la ficha científica de GBIF.',
    placeholder_buscar: 'Ej: mosca blanca, Bemisia tabaci…',
    btn_buscar:       'Buscar todo',
    label_local:      'BD Local',
    sub_local:        'bitácora interna',
    label_gbif:       'GBIF',
    sub_gbif:         'ficha científica',
    titulo_imagen:    '<span data-i18n="titulo_imagen">Identificar Plaga por Imagen</span>',
    desc_imagen:      'Sube una foto de la plaga y el sistema la identificará automáticamente usando inteligencia artificial.',
    drop_title:       'Haz clic o arrastra una imagen aquí',
    drop_sub:         'JPG, PNG, WEBP — máx. 5MB',
    btn_identificar:  '📖 Identificar plaga',
    analizando:       'Analizando imagen con IA…',
    titulo_registrar: '<span data-i18n="titulo_registrar">Registrar Nueva Plaga</span>',
    desc_registrar:   'Añade un nuevo registro a la bitácora local de AgroGuard.',
    label_nombre:     'NOMBRE *',
    label_ncientifico:'NOMBRE CIENTÍFICO *',
    label_familia:    'FAMILIA *',
    label_reino:      'REINO *',
    label_riesgo:     'RIESGO *',
    label_fecha:      'FECHA *',
    label_ficha:      'FICHA TÉCNICA *',
    placeholder_ficha:'Describe características, síntomas, ciclo de vida, tratamiento recomendado…',
    label_ubicacion:  'UBICACIÓN DEL FOCO',
    btn_detectar:     '📍 Detectar',
    btn_guardar:      '+ Guardar en bitácora',
    opt_seleccionar:  '— Seleccionar —',
    opt_alto:         '⚠️ Alto',
    opt_medio:        '⚠️ Medio',
    opt_bajo:         '⚠️ Bajo',
    titulo_mapa:      '<span data-i18n="titulo_mapa">Mapa de Focos de Infección</span>',
    desc_mapa:        'Visualiza todos los focos registrados con ubicación geográfica.',
    btn_actualizar:   '⟳ Actualizar mapa',
    daltonismo_titulo:'MODO DALTONISMO',
    f_normal:         '— Sin filtro',
    f_protanopia:     '— Protanopia (rojo)',
    f_deuteranopia:   '— Deuteranopia (verde)',
    f_tritanopia:     '— Tritanopia (azul)',
    f_achromatopsia:  '— Acromatopsia (sin color)',
  },
  en: {
    subtitulo:        'PEST MANAGEMENT SYSTEM · v1.0',
    btn_pdf:          'PDF REPORT',
    tab_consultar:    'Search',
    tab_imagen:       'Image',
    tab_registrar:    'Register',
    tab_mapa:         'Map',
    titulo_consultar: 'Integrated Pest Search',
    desc_consultar:   'Enter a name and get local records and scientific data from GBIF simultaneously.',
    placeholder_buscar:'E.g.: whitefly, Bemisia tabaci…',
    btn_buscar:       'Search all',
    label_local:      'Local DB',
    sub_local:        'internal log',
    label_gbif:       'GBIF',
    sub_gbif:         'scientific data',
    titulo_imagen:    'Identify Pest by Image',
    desc_imagen:      'Upload a photo of the pest and the system will identify it automatically using artificial intelligence.',
    drop_title:       'Click or drag an image here',
    drop_sub:         'JPG, PNG, WEBP — max 5MB',
    btn_identificar:  '📖 Identify pest',
    analizando:       'Analyzing image with AI…',
    titulo_registrar: 'Register New Pest',
    desc_registrar:   'Add a new record to the AgroGuard local log.',
    label_nombre:     'NAME *',
    label_ncientifico:'SCIENTIFIC NAME *',
    label_familia:    'FAMILY *',
    label_reino:      'KINGDOM *',
    label_riesgo:     'RISK *',
    label_fecha:      'DATE *',
    label_ficha:      'TECHNICAL SHEET *',
    placeholder_ficha:'Describe characteristics, symptoms, life cycle, recommended treatment…',
    label_ubicacion:  'OUTBREAK LOCATION',
    btn_detectar:     '📍 Detect',
    btn_guardar:      '+ Save to log',
    opt_seleccionar:  '— Select —',
    opt_alto:         '⚠️ High',
    opt_medio:        '⚠️ Medium',
    opt_bajo:         '⚠️ Low',
    titulo_mapa:      'Infection Focus Map',
    desc_mapa:        'View all registered outbreak locations on the map.',
    btn_actualizar:   '⟳ Refresh map',
    riesgo_alto:      '⚠️ High',
    riesgo_medio:     '⚠️ Medium',
    riesgo_bajo:      '⚠️ Low',
    placeholder_lat:  'Latitude',
    placeholder_lng:       'Longitude',
    placeholder_ncientifico: 'E.g.: Bemisia tabaci',
    placeholder_familia:     'E.g.: Aleyrodidae',
    placeholder_reino:       'E.g.: Animalia',
    daltonismo_titulo:       'COLORBLIND MODE',
    f_normal:         '— No filter',
    f_protanopia:     '— Protanopia (red)',
    f_deuteranopia:   '— Deuteranopia (green)',
    f_tritanopia:     '— Tritanopia (blue)',
    f_achromatopsia:  '— Achromatopsia (no color)',
  },
  pt: {
    subtitulo:        'SISTEMA DE GESTÃO DE PRAGAS · v1.0',
    btn_pdf:          'RELATÓRIO PDF',
    tab_consultar:    'Consultar',
    tab_imagen:       'Imagem',
    tab_registrar:    'Registrar',
    tab_mapa:         'Mapa',
    titulo_consultar: 'Consulta Integral de Pragas',
    desc_consultar:   'Digite um nome e obtenha registros locais e dados científicos do GBIF simultaneamente.',
    placeholder_buscar:'Ex: mosca branca, Bemisia tabaci…',
    btn_buscar:       'Buscar tudo',
    label_local:      'BD Local',
    sub_local:        'diário interno',
    label_gbif:       'GBIF',
    sub_gbif:         'ficha científica',
    titulo_imagen:    'Identificar Praga por Imagem',
    desc_imagen:      'Envie uma foto da praga e o sistema a identificará automaticamente usando inteligência artificial.',
    drop_title:       'Clique ou arraste uma imagem aqui',
    drop_sub:         'JPG, PNG, WEBP — máx. 5MB',
    btn_identificar:  '📖 Identificar praga',
    analizando:       'Analisando imagem com IA…',
    titulo_registrar: 'Registrar Nova Praga',
    desc_registrar:   'Adicione um novo registro ao diário local do AgroGuard.',
    label_nombre:     'NOME *',
    label_ncientifico:'NOME CIENTÍFICO *',
    label_familia:    'FAMÍLIA *',
    label_reino:      'REINO *',
    label_riesgo:     'RISCO *',
    label_fecha:      'DATA *',
    label_ficha:      'FICHA TÉCNICA *',
    placeholder_ficha:'Descreva características, sintomas, ciclo de vida, tratamento recomendado…',
    label_ubicacion:  'LOCALIZAÇÃO DO FOCO',
    btn_detectar:     '📍 Detectar',
    btn_guardar:      '+ Salvar no diário',
    opt_seleccionar:  '— Selecionar —',
    opt_alto:         '⚠️ Alto',
    opt_medio:        '⚠️ Médio',
    opt_bajo:         '⚠️ Baixo',
    titulo_mapa:      'Mapa de Focos de Infecção',
    desc_mapa:        'Visualize todos os focos registrados com localização geográfica.',
    btn_actualizar:   '⟳ Atualizar mapa',
    riesgo_alto:      '⚠️ Alto',
    riesgo_medio:     '⚠️ Médio',
    riesgo_bajo:      '⚠️ Baixo',
    placeholder_lat:  'Latitude',
    placeholder_lng:       'Longitude',
    placeholder_ncientifico: 'Ex: Bemisia tabaci',
    placeholder_familia:     'Ex: Aleyrodidae',
    placeholder_reino:       'Ex: Animalia',
    daltonismo_titulo:       'MODO DALTONISMO',
    f_normal:         '— Sem filtro',
    f_protanopia:     '— Protanopia (vermelho)',
    f_deuteranopia:   '— Deuteranopia (verde)',
    f_tritanopia:     '— Tritanopia (azul)',
    f_achromatopsia:  '— Acromatopsia (sem cor)',
  }
};

export let idiomaActual = 'es';

export function cambiarIdioma(lang) {
  idiomaActual = lang;
  const t = i18n[lang];
  // Update subtitle in header
  document.querySelectorAll('.mono').forEach(el => {
    const txt = el.textContent;
    if (txt.includes('SISTEMA DE') || txt.includes('PEST MANAGEMENT') || txt.includes('GESTÃO DE')) {
      el.textContent = t.subtitulo;
    }
  });
  // Update tabs
  const tabTextos = { consultar: t.tab_consultar, imagen: t.tab_imagen, registrar: t.tab_registrar, mapa: t.tab_mapa };
  const iconMap = { consultar: '🔍', imagen: '🖼️', registrar: '➕', mapa: '🗺️' };
  Object.entries(tabTextos).forEach(([id, texto]) => {
    const btn = document.getElementById(`tab-${id}`);
    if (btn) btn.innerHTML = `<span style="margin-right:.35rem;">${iconMap[id]}</span> ${texto}`;
  });
  // Translate elements with data-i18n attributes
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (!t[key]) return;
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      el.placeholder = t[key];
    } else if (el.tagName === 'OPTION') {
      el.textContent = t[key];
    } else {
      el.textContent = t[key];
    }
  });
  // Voice synthesis language mapping
  const langVoz = { es: 'es-MX', en: 'en-US', pt: 'pt-BR' };
  globalThis._vozLang = langVoz[lang];
  if (window.lectorActivo) { speechSynthesis.cancel(); }
  showToast(`🌐 ${lang === 'es' ? 'Español' : lang === 'en' ? 'English' : 'Português'}`, 'success');
}
