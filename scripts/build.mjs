import { readFile } from 'node:fs/promises';
import { errorsFor } from '../lib/validation.js';

// No framework build is needed. Ensure the assets and schema ship together.
await Promise.all(['web/index.html', 'web/styles.css', 'web/app.js', 'web/favicon.svg', 'assets/site-config.json'].map(path => readFile(path)));
if (errorsFor({}).length === 0) throw new Error('テーマスキーマが無効です');
console.log('静的サイトと共有JSONスキーマを確認しました。');
