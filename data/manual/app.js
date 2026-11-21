/* SPDX-License-Identifier: MIT */
(() => {
  'use strict';
  const manuals = JSON.parse(document.getElementById('manual-data').textContent);
  const key = 'grandma-linux-manual-v1';
  const ids = manuals.en.topics.map(topic => topic.id);
  let saved = {}, storageAvailable = true;
  try { saved = JSON.parse(localStorage.getItem(key) || '{}') || {}; }
  catch (_) { storageAvailable = false; }
  const hash = new URLSearchParams(location.hash.slice(1));
  const validLanguage = language => ['en', 'pt-BR'].includes(language);
  let language = validLanguage(hash.get('lang')) ? hash.get('lang') :
    validLanguage(saved.language) ? saved.language : document.documentElement.lang;
  if (!validLanguage(language)) language = 'en';
  let current = ids.includes(hash.get('chapter')) ? hash.get('chapter') : ids.includes(saved.current) ? saved.current : ids[0];
  let favorites = new Set(Array.isArray(saved.favorites) ? saved.favorites.filter(id => ids.includes(id)) : []);
  let theme = ['dark', 'light'].includes(saved.theme) ? saved.theme : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  let scale = Number.isFinite(saved.scale) ? Math.min(2, Math.max(1, saved.scale)) : 1;
  let favoritesOnly = false;
  const $ = id => document.getElementById(id);
  const labels = {
    'pt-BR': { manual:'Manual de uso', edition:'SEU GUIA DO DIA A DIA', title:'Seu computador, passo a passo.', cover:'Escolha um capítulo para começar.', all:'Capítulos', favorites:'Favoritos', empty:'Seus favoritos aparecem aqui. Marque uma página com a estrela para guardar.', offline:'Disponível sem internet.', chapter:'CAPÍTULO', save:'☆ Guardar nos favoritos', remove:'★ Remover dos favoritos', result:'O que acontece', previous:'← Anterior', next:'Próxima →', page:'Página', of:'de', dark:'Tema escuro', light:'Tema claro', language:'Idioma do manual', preferences:'Preferências de leitura', smaller:'Diminuir o texto', larger:'Aumentar o texto', footer:'Grandma Linux · Seus favoritos e preferências ficam neste navegador.', warning:'Este navegador não conseguiu salvar suas preferências. Elas serão mantidas apenas nesta janela.' },
    en: { manual:'User manual', edition:'YOUR EVERYDAY GUIDE', title:'Your computer, step by step.', cover:'Select a chapter to start.', all:'Chapters', favorites:'Favorites', empty:'Your favorites appear here. Use the star on a page to save it.', offline:'Available without internet.', chapter:'CHAPTER', save:'☆ Save to favorites', remove:'★ Remove from favorites', result:'What happens', previous:'← Previous', next:'Next →', page:'Page', of:'of', dark:'Dark theme', light:'Light theme', language:'Manual language', preferences:'Reading preferences', smaller:'Make text smaller', larger:'Make text larger', footer:'Grandma Linux · Your favorites and preferences stay in this browser.', warning:'This browser could not save your preferences. They will stay only in this window.' }
  };
  function persist() {
    try { localStorage.setItem(key, JSON.stringify({language, current, theme, scale, favorites:[...favorites]})); }
    catch (_) { storageAvailable = false; }
  }
  function text(id, value) { $(id).textContent = value; }
  function renderNavigation() {
    const l = labels[language];
    const list = $('chapters'); list.replaceChildren();
    manuals[language].topics.forEach((topic, index) => {
      if (favoritesOnly && !favorites.has(topic.id)) return;
      const item = document.createElement('li');
      const button = document.createElement('button'); button.type = 'button';
      button.dataset.chapter = topic.id;
      if (topic.id === current) button.setAttribute('aria-current', 'page');
      const number = document.createElement('span'); number.className = 'chapter-index'; number.textContent = String(index + 1).padStart(2, '0'); number.setAttribute('aria-hidden', 'true');
      const title = document.createElement('span'); title.textContent = topic.title;
      button.append(number, title);
      if (favorites.has(topic.id)) { const star = document.createElement('span'); star.className = 'chapter-star'; star.textContent = '★'; star.setAttribute('aria-hidden', 'true'); button.append(star); }
      button.addEventListener('click', () => navigate(topic.id));
      item.append(button); list.append(item);
    });
    $('empty-favorites').hidden = !(favoritesOnly && favorites.size === 0);
    text('empty-favorites', l.empty);
    text('show-all', l.all); text('show-favorites', l.favorites + ' · ' + favorites.size);
    $('show-all').setAttribute('aria-pressed', String(!favoritesOnly));
    $('show-favorites').setAttribute('aria-pressed', String(favoritesOnly));
  }
  function render() {
    const l = labels[language], manual = manuals[language];
    const index = ids.indexOf(current), topic = manual.topics[index];
    document.documentElement.lang = language;
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.setProperty('--text-scale', scale);
    document.title = 'Grandma Linux — ' + l.manual;
    text('book-label', l.manual); text('edition-label', l.edition); text('contents-heading', l.title); text('cover-note', l.cover);
    text('offline-note', l.offline); text('chapter-number', l.chapter + ' ' + String(index + 1).padStart(2, '0'));
    text('chapter-title', topic.title); text('before', topic.before || ''); $('before').hidden = !topic.before;
    $('steps').replaceChildren(...topic.steps.map(step => { const li = document.createElement('li'); const span = document.createElement('span'); span.textContent = step; li.append(span); return li; }));
    text('result-label', l.result); text('result', topic.result); text('tip', topic.tip || ''); $('tip').hidden = !topic.tip;
    text('favorite', favorites.has(current) ? l.remove : l.save);
    $('favorite').setAttribute('aria-pressed', String(favorites.has(current)));
    text('previous', l.previous); text('next', l.next);
    $('previous').disabled = index === 0; $('next').disabled = index === ids.length - 1;
    text('page-count', `${l.page} ${index + 1} ${l.of} ${ids.length}`);
    $('language').value = language; text('language-label', l.language);
    $('preferences').setAttribute('aria-label', l.preferences);
    $('filters').setAttribute('aria-label', l.all); $('chapter-nav').setAttribute('aria-label', l.all);
    text('theme-toggle', theme === 'light' ? l.dark : l.light);
    $('theme-toggle').setAttribute('aria-pressed', String(theme === 'dark'));
    $('smaller').setAttribute('aria-label', l.smaller); $('larger').setAttribute('aria-label', l.larger);
    $('smaller').disabled = scale <= 1; $('larger').disabled = scale >= 2;
    text('colophon', l.footer); text('storage-warning', l.warning); $('storage-warning').hidden = storageAvailable;
    renderNavigation();
  }
  function update() { persist(); render(); }
  function navigate(id) {
    current = id; update();
    $('article').focus({preventScroll:true});
    if (matchMedia('(max-width: 800px)').matches) $('article').scrollIntoView({block:'start'});
  }
  $('language').addEventListener('change', event => { language = event.target.value; update(); });
  $('theme-toggle').addEventListener('click', () => { theme = theme === 'light' ? 'dark' : 'light'; update(); });
  $('favorite').addEventListener('click', () => { favorites.has(current) ? favorites.delete(current) : favorites.add(current); update(); });
  $('show-all').addEventListener('click', () => { favoritesOnly = false; renderNavigation(); });
  $('show-favorites').addEventListener('click', () => { favoritesOnly = true; renderNavigation(); });
  $('previous').addEventListener('click', () => navigate(ids[Math.max(0, ids.indexOf(current) - 1)]));
  $('next').addEventListener('click', () => navigate(ids[Math.min(ids.length - 1, ids.indexOf(current) + 1)]));
  $('smaller').addEventListener('click', () => { scale = Math.max(1, Math.round((scale - .1) * 10) / 10); update(); });
  $('larger').addEventListener('click', () => { scale = Math.min(2, Math.round((scale + .1) * 10) / 10); update(); });
  document.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || ['INPUT','TEXTAREA','SELECT','BUTTON'].includes(document.activeElement.tagName)) return;
    if (event.key === 'ArrowRight' && !$('next').disabled) { event.preventDefault(); navigate(ids[ids.indexOf(current) + 1]); }
    if (event.key === 'ArrowLeft' && !$('previous').disabled) { event.preventDefault(); navigate(ids[ids.indexOf(current) - 1]); }
  });
  update();
})();
