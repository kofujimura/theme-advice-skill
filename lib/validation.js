import { readFileSync } from 'node:fs';
import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

export const MAX_BYTES = 65536;
export const UUID = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const schema = JSON.parse(readFileSync(new URL('../assets/public-theme.schema.json', import.meta.url), 'utf8'));
const validate = ajv.compile(schema);

export function errorsFor(theme) {
  if (!validate(theme)) return validate.errors.map(error => `${error.instancePath || '/'}: ${error.message}`);
  const errors = [];
  const sources = new Map(theme.sources.map(source => [source.id, source]));
  if (sources.size !== theme.sources.length) errors.push('資料IDが重複しています');
  for (const source of theme.sources) {
    if (source.url) {
      try {
        const url = new URL(source.url);
        if (!url.hostname || url.username || url.password) errors.push('資料URLには認証情報を含まないHTTP(S) URLを指定してください');
      } catch { errors.push('資料URLの形式を確認してください'); }
    }
  }
  for (const [ids, needsEvidence] of [
    [theme.theme.source_ids, theme.theme.novelty.status === 'search_scoped'],
    [theme.theme.technology.source_ids, theme.theme.technology.availability === 'verified'],
  ]) {
    if (ids.some(id => !sources.has(id))) errors.push('存在しない資料IDが含まれています');
    if (needsEvidence && !ids.some(id => ['full_text', 'abstract'].includes(sources.get(id)?.read_level))) {
      errors.push('確認済みの根拠となる資料が必要です');
    }
  }
  return errors;
}

export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}
