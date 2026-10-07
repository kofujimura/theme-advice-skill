// Exercise the actual installed Python sender against the local HTTP API.
// This creates four explicitly fictional themes, only at localhost.
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

if (process.env.VERCEL || process.env.THEME_STORAGE !== 'local' || !process.env.THEME_SUBMIT_TOKEN) {
  throw new Error('ローカル開発用の.env.localを指定して実行してください');
}
const base = `http://localhost:${process.env.PORT || 3210}`;
const directory = await mkdtemp(join(tmpdir(), 'theme-sharing-smoke-'));
const installed = join(directory, 'skill');
const run = (script, args) => execFileSync('python3', [script, ...args], { encoding: 'utf8', env: { ...process.env, THEME_SITE_URL: base } });
run(resolve('scripts/install.py'), ['--dest', installed]);
const fixture = JSON.parse(await readFile(new URL('./public-theme.fixture.json', import.meta.url), 'utf8'));
const variants = [
  [fixture.theme.title, fixture.theme.rq, 'problem', 'そら'],
  ['対話の途中で好みが変わると、AIの推薦はどう変わるか', '好みの変更をAIに伝えるタイミングは、推薦への納得と説明の理解にどう影響するか？', 'application', 'なつ'],
  ['「前の誰か」を引き継ぐ、記憶するインスタレーション', '前の鑑賞者の反応が残る作品で、鑑賞者は自分と他者の存在をどのように語るか？', 'artistic', 'うみ'],
  ['エージェント同士の取引で、合意の食い違いはどこで起きるか', '模擬的な価値交換で、合意の記録方法は条件の食い違いの発見にどう影響するか？', 'technical', 'りく'],
];
for (let index = 0; index < variants.length; index++) {
  const path = join(directory, 'student-' + index);
  const workspace = join(installed, 'scripts/workspace.py');
  const share = join(installed, 'scripts/share.py');
  run(workspace, ['init', '--workspace', path]);
  const session = JSON.parse(await readFile(join(path, 'session.json'), 'utf8'));
  const [title, rq, kind, name] = variants[index];
  session.student.nickname = 'デモ：' + name;
  session.student.own_words = ['PRIVATE: test-only dialogue, never submit'];
  const theme = structuredClone(fixture.theme);
  Object.assign(theme, { id: 'C1', title, rq, contribution_types: [kind], novelty_status: 'unverified', novelty_claim: theme.novelty.claim,
    student_feedback: [], readiness: Object.fromEntries(['interest', 'question', 'novelty', 'evaluation', 'feasibility', 'ownership'].map(key => [key, 'unknown'])) });
  delete theme.novelty;
  // Demonstration themes are illustrative, not literature-checked proposals.
  if (index) {
    theme.novelty_claim = '動作確認用の架空のテーマ。先行研究との差はまだ調べていません。';
    theme.technology.capability = index === 2 ? '鑑賞者の反応を次の体験へ引き継ぐ仕組み' : '状況に応じて行動を選ぶAIエージェント';
    theme.evaluation = { comparison: '条件を変えた小さな試行で比べる。具体的な条件はこれから検討。', metrics: index === 2 ? ['鑑賞者による体験の記述'] : ['違いを判断する観点はこれから検討'], procedure: 'まず試行して観察方法が成立するか確かめる。', resources: '利用条件や協力者は未確認。', limitations: 'まだ具体化していない部分がある。' };
  }
  session.candidates = [theme]; session.selected_candidate_id = 'C1';
  session.decisions = [{ at: new Date().toISOString(), actor: 'student', action: 'select', candidate_id: 'C1', reason: '架空の学生の動作確認', student_quote: null }];
  await writeFile(join(path, 'session.json'), JSON.stringify(session, null, 2));
  run(workspace, ['validate', '--workspace', path]);
  run(share, ['--workspace', path, 'export']);
  const exported = JSON.parse(await readFile(join(path, 'theme.json'), 'utf8'));
  assert.ok(!JSON.stringify(exported).includes('PRIVATE'));
  run(share, ['--workspace', path, 'send', '--allow-local-http']);
  run(share, ['--workspace', path, 'send', '--allow-local-http']);
  const receipt = JSON.parse(await readFile(join(path, 'submission.json'), 'utf8'));
  assert.equal(receipt.status, 'sent'); assert.equal(receipt.duplicate, true);
  const response = await fetch(base + '/api/themes?id=' + exported.id);
  assert.equal(response.status, 200);
  const record = await response.json(); assert.equal(record.author.nickname, 'デモ：' + name);
  const idRequest = await fetch(base + '/api/themes', { method: 'POST', body: JSON.stringify(exported), headers: { 'Content-Type': 'application/json' } });
  assert.equal(idRequest.status, 401);
}
console.log('導入済みスキルからのJSON保存→HTTP送信→再送→閲覧を確認しました（架空の4テーマ）。');
console.log('検査用ワークスペース: ' + directory);
