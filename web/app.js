const labels = { technical: '技術の新しさ', application: '応用の新しさ', problem: '問題の新しさ', artistic: '表現・体験の新しさ' };
const noveltyLabels = { unverified: '先行研究を未確認', search_scoped: '調べた範囲で差を整理', teacher_reviewed: '教員に相談済み' };
const technologyLabels = { unverified: '利用条件は未確認', verified: '利用条件を確認済み', unavailable: '現状では利用困難' };
const readingLabels = { full_text: '本文を確認', abstract: '要旨を確認', snippet: '検索結果のみ', unread: '未読' };
const $ = id => document.getElementById(id);
const state = { themes: [], cursor: null, filter: 'all', loading: false, detailId: null };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function date(value) {
  return new Intl.DateTimeFormat('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value));
}
function badge(kind) {
  const node = el('span', 'badge', labels[kind]);
  node.dataset.kind = kind;
  return node;
}
function novelty(status) {
  const node = el('span', 'novelty-status', noveltyLabels[status]);
  node.dataset.status = status;
  return node;
}
function author(nickname) {
  const node = el('div', 'card-author');
  const avatar = el('span', 'avatar', [...nickname][0]);
  avatar.setAttribute('aria-hidden', 'true');
  node.append(avatar, el('span', 'nickname', nickname));
  return node;
}
async function fetchJSON(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || '読み込めませんでした');
  return value;
}
function card(record) {
  const node = el('article', 'theme-card');
  const top = el('div', 'card-top');
  top.append(...record.theme.contribution_types.map(badge));
  const heading = el('h3');
  const link = el('a', 'card-link', record.theme.title);
  link.href = '/?theme=' + record.id;
  link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    showDetail(record.id, true);
  });
  heading.append(link);
  const rq = el('div', 'rq');
  rq.append(el('span', 'rq-label', 'RESEARCH QUESTION'), el('p', '', record.theme.rq));
  const bottom = el('div', 'card-bottom');
  bottom.append(author(record.author.nickname), novelty(record.theme.novelty.status));
  node.append(top, heading, rq, bottom, el('p', 'card-date', date(record.submitted_at) + ' に共有'));
  return node;
}
function empty(title, text, action, label) {
  const node = el('div', 'empty');
  const symbol = el('div', 'empty-symbol', '?');
  symbol.setAttribute('aria-hidden', 'true');
  node.append(symbol, el('h3', '', title), el('p', '', text));
  if (action) {
    const button = el('button', 'primary', label);
    button.type = 'button';
    button.addEventListener('click', action);
    node.append(button);
  }
  return node;
}
function render() {
  const query = $('search').value.trim().toLocaleLowerCase('ja');
  const filtered = state.themes.filter(record => {
    const matchesType = state.filter === 'all' || record.theme.contribution_types.includes(state.filter);
    const haystack = [record.theme.title, record.theme.rq, record.author.nickname, record.theme.interest_connection, record.theme.technology.capability].join('\n').toLocaleLowerCase('ja');
    return matchesType && (!query || haystack.includes(query));
  }).sort((a, b) => b.submitted_at.localeCompare(a.submitted_at) || a.id.localeCompare(b.id));
  $('theme-list').replaceChildren(...filtered.map(card));
  if (!filtered.length && !state.loading) {
    if (!state.themes.length) $('theme-list').append(empty('最初の問いを持ち寄ろう。', 'AIとの対話で生まれたテーマを、ここに共有できます。まだ確かめていないことも、次の一歩と一緒に残しましょう。', () => $('help').showModal(), 'テーマの共有方法を見る'));
    else $('theme-list').append(empty('この条件のテーマは見つかりません。', state.cursor ? '検索語や切り口を変えてみてください。まだ読み込んでいないテーマは、下のボタンから表示できます。' : '検索語や新しさの切り口を変えて、ほかの問いも見てみましょう。', () => {
      $('search').value = ''; setFilter('all');
    }, '絞り込みを解除する'));
  }
  $('total-count').textContent = state.themes.length + (state.cursor ? '+' : '');
  $('result-count').textContent = `${filtered.length}件を表示` + (state.cursor ? ` / ${state.themes.length}件読み込み済み・続きあり` : '');
  for (const node of document.querySelectorAll('[data-count]')) {
    node.textContent = node.dataset.count === 'all' ? state.themes.length : state.themes.filter(record => record.theme.contribution_types.includes(node.dataset.count)).length;
  }
  $('load-more').hidden = !state.cursor;
  $('load-more').disabled = state.loading;
}
function setFilter(filter) {
  state.filter = filter;
  for (const button of $('filters').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.filter === filter));
  $('list-title').textContent = filter === 'all' ? 'すべてのテーマ' : labels[filter];
  render();
}
async function loadThemes(more = false) {
  if (state.loading) return;
  state.loading = true;
  $('theme-list').setAttribute('aria-busy', 'true');
  $('load-more').disabled = true;
  $('notice').hidden = true;
  if (!more) $('theme-list').replaceChildren(el('p', 'loading', 'みんなの問いを読み込んでいます…'));
  try {
    const page = await fetchJSON('/api/themes' + (more && state.cursor ? '?cursor=' + encodeURIComponent(state.cursor) : ''));
    const records = more ? [...state.themes, ...page.themes] : page.themes;
    state.themes = [...new Map(records.map(record => [record.id.toLowerCase(), record])).values()];
    state.cursor = page.next_cursor;
    state.loading = false;
    render();
  } catch (error) {
    const notice = $('notice');
    notice.replaceChildren(el('span', '', error.message));
    const retry = el('button', '', '再読み込み');
    retry.addEventListener('click', () => loadThemes(more));
    notice.append(retry);
    notice.hidden = false;
    $('result-count').textContent = more ? `${state.themes.length}件読み込み済み` : 'テーマを読み込めませんでした';
    if (!more) $('theme-list').replaceChildren();
  } finally {
    state.loading = false;
    $('theme-list').setAttribute('aria-busy', 'false');
    $('load-more').disabled = false;
  }
}
function section(title, text) {
  const node = el('section', 'detail-section');
  node.append(el('h3', '', title));
  if (text !== undefined) node.append(el('p', '', text || 'これから検討します。'));
  return node;
}
function definitions(values) {
  const node = el('dl');
  for (const [label, value] of values) node.append(el('dt', '', label), el('dd', '', value || 'これから検討します。'));
  return node;
}
async function copy(text, status) {
  try { await navigator.clipboard.writeText(text); status.textContent = 'コピーしました。'; }
  catch { status.textContent = 'コピーできませんでした。表示された文章やURLを選択してコピーしてください。'; }
}
function detail(record) {
  const theme = record.theme;
  const body = $('detail-body');
  const types = el('div', 'card-top');
  types.append(...theme.contribution_types.map(badge));
  const title = el('h2', '', theme.title);
  title.id = 'detail-title';
  const meta = el('div', 'detail-meta');
  meta.append(author(record.author.nickname), el('span', '', date(record.submitted_at) + ' に共有'));
  const rq = el('div', 'detail-rq');
  rq.append(el('span', 'rq-label', 'RESEARCH QUESTION'), el('p', '', theme.rq));
  const interest = section('この問いにつながる興味', theme.interest_connection);
  const newness = section('新しさの仮説');
  const status = el('div', 'section-status');
  status.append(novelty(theme.novelty.status));
  newness.append(status, el('p', '', theme.novelty.claim || '先行研究との差は、これから調べます。'));
  const technology = section('活用する技術');
  technology.append(definitions([['新しい能力', theme.technology.capability], ['利用可能性', technologyLabels[theme.technology.availability]], ['利用条件', theme.technology.conditions]]));
  const evaluation = section('どう確かめるか');
  evaluation.append(definitions([['比較対象', theme.evaluation.comparison], ['指標・観点', theme.evaluation.metrics.join('\n')], ['手順', theme.evaluation.procedure], ['必要な資源', theme.evaluation.resources], ['限界・偏り', theme.evaluation.limitations]]));
  const pilot = section('最初の小さな実験', theme.pilot);
  const questions = section('これから確かめること');
  const list = el('ul');
  list.append(...theme.open_questions.map(text => el('li', '', text)));
  questions.append(theme.open_questions.length ? list : el('p', '', '未確認事項は現在記載されていません。'));
  const sources = section('参考にした資料');
  if (!record.sources.length) sources.append(el('p', 'subtle', '資料はまだ登録されていません。'));
  for (const source of record.sources) {
    const node = el('div', 'source');
    let link = el('span', '', source.id + ' · ' + source.title);
    if (source.url && /^https?:\/\//.test(source.url)) {
      link = el('a', '', source.id + ' · ' + source.title);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    }
    node.append(link, el('p', 'source-meta', readingLabels[source.read_level] + (source.checked_at ? ' / ' + date(source.checked_at) + '確認' : '')),
      el('p', '', source.takeaway));
    sources.append(node);
  }
  const actions = el('div', 'detail-actions');
  const download = el('button', 'secondary', 'テーマJSONを保存');
  download.addEventListener('click', () => {
    const { submitted_at, ...payload } = record;
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2) + '\n'], { type: 'application/json' }));
    const link = el('a'); link.href = url; link.download = 'theme-' + record.id + '.json';
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  const copyLink = el('button', 'secondary', 'このテーマのURLをコピー');
  const copyStatus = el('p', 'subtle');
  copyStatus.setAttribute('role', 'status');
  copyLink.addEventListener('click', () => copy(location.origin + '/?theme=' + record.id, copyStatus));
  actions.append(download, copyLink, copyStatus);
  body.replaceChildren(types, title, meta, rq, interest, newness, technology, evaluation, pilot, questions, sources, actions);
}
async function showDetail(id, push = false) {
  state.detailId = id.toLowerCase();
  if (push) { const url = new URL(location.href); url.searchParams.set('theme', id); history.pushState({}, '', url); }
  const dialog = $('detail');
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
  const loading = el('h2', 'detail-loading', 'テーマを読み込んでいます…');
  loading.id = 'detail-title';
  $('detail-body').replaceChildren(loading);
  try {
    const record = state.themes.find(theme => theme.id.toLowerCase() === id.toLowerCase()) || await fetchJSON('/api/themes?id=' + encodeURIComponent(id));
    if (state.detailId === id.toLowerCase()) detail(record);
  } catch (error) {
    if (state.detailId !== id.toLowerCase()) return;
    const title = el('h2', '', 'テーマを表示できませんでした'); title.id = 'detail-title';
    const retry = el('button', 'secondary', 'もう一度読み込む'); retry.addEventListener('click', () => showDetail(id));
    $('detail-body').replaceChildren(title, el('p', 'subtle', error.message), retry);
  }
}
function route() {
  const id = new URL(location.href).searchParams.get('theme');
  if (id) showDetail(id);
  else if ($('detail').open) $('detail').close();
}
$('filters').addEventListener('click', event => {
  const button = event.target.closest('button[data-filter]');
  if (button) setFilter(button.dataset.filter);
});
$('search').addEventListener('input', render);
$('load-more').addEventListener('click', () => loadThemes(true));
$('open-help').addEventListener('click', () => $('help').showModal());
$('copy-command').addEventListener('click', () => copy('このテーマを保存して、テーマを送る。', $('copy-status')));
for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => $(button.dataset.close).close());
for (const dialog of [$('detail'), $('help')]) {
  let startedOutside = false;
  const outside = event => {
    const rect = dialog.getBoundingClientRect();
    return event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom);
  };
  dialog.addEventListener('pointerdown', event => { startedOutside = outside(event); });
  dialog.addEventListener('click', event => {
    if (startedOutside && outside(event)) dialog.close();
    startedOutside = false;
  });
}
$('detail').addEventListener('close', () => {
  state.detailId = null;
  if (new URL(location.href).searchParams.has('theme')) {
    const url = new URL(location.href); url.searchParams.delete('theme'); history.pushState({}, '', url);
  }
});
window.addEventListener('popstate', route);
loadThemes();
route();
