# テーマ広場を新しいVercelプロジェクトで公開する

2026-10-07に新規プロジェクト `kofujimuras-projects/theme-advice` を作成し、[テーマ広場](https://theme-advice.vercel.app) に公開しました。専用のPrivate Blobストアと、本番の `THEME_SUBMIT_TOKEN` を設定済みです。スキルの送信先もこのURLに設定しています。

教員用の送信キーは、ローカルの `tmp/vercel-submit-token.txt` に権限600で保存しています。Gitの除外対象で、サイトにも同梱しません。この値を学生に別途案内し、学生はREADMEの非表示入力で設定します。Vercelの管理用トークンではありません。

このリポジトリのルートをVercelプロジェクトにします。スキルのGitHub公開は任意で、サイトはVercel CLIからもデプロイできます。Vercelアカウントと、Private Blobストアを作成・接続できる権限が必要です。

## サイトの構成

- `web/`：共有されたテーマの一覧、検索、絞り込み、詳細、JSON保存、共有方法。
- `api/themes.js`：GETで閲覧、POSTで受け付けるNode.js Function。
- `assets/public-theme.schema.json`：Pythonとサーバーで共通の共有形式。
- Private Vercel Blob：テーマごとに `themes/<UUID>.json` を永続保存。1件ずつ上書き禁止で保存し、再送時の内容を比較する。

閲覧はログインなし、投稿にはゼミ共通のキーを使います。ニックネームは自己申告で、本人確認の機能ではありません。検索エンジン向けに `noindex` を設定しますが、URLからの閲覧は制限しません。公開済み投稿を修正したい場合は、新しいJSONを投稿します。削除が必要な場合は教員がBlobストアで対象IDを確認して対応します。

## 1. ローカルで確認する

Node.js 20以上を使います。次は教員・開発者向けの操作で、学生がスキルを使うだけなら不要です。

```bash
npm ci
cp .env.example .env.local
```

`.env.local` の `THEME_SUBMIT_TOKEN` を、空白を含まない24文字以上のランダムなキーに変更します。`.env.local` と `.theme-site-data/` はGitの除外対象です。

```bash
npm run dev
```

ブラウザで `http://localhost:3210` を開きます。保存先は開発用の `.theme-site-data/` です。Vercel上でローカル保存を指定すると、意図的にエラーになります。

別のターミナルから、スキルで作った共有JSONの送信を確認できます。`THEME_SUBMIT_TOKEN` を上の値と揃え、URLを `http://localhost:3210` に設定します。ローカル開発時の `configure` と `send` にだけ `--allow-local-http` を付けます。本番URLはHTTPSです。

## 2. 新規Vercelプロジェクトを用意する

GitHub公開後は、Vercelで **Add New → Project** からこのリポジトリをImportします。

| 設定 | 値 |
| --- | --- |
| Project Name | `theme-advice` など空いている名前 |
| Framework Preset | Other |
| Root Directory | リポジトリのルート |
| Build Command | `npm run build` |
| Output Directory | `web` |
| Install Command | `npm ci` |
| Node.js | 20以上のサポートされる版 |

`vercel.json` にFunctionと静的ファイルの設定を含みます。APIは `/api/themes` です。[Vercel公式のNode.js Functions](https://vercel.com/docs/functions/runtimes/node-js)

GitHubから取り込まずに公開する場合は、Vercel CLIを利用します。グローバルインストールは不要です。

```bash
npx vercel login
npx vercel
```

新しいプロジェクトを作成して、このルートディレクトリを選びます。初回は保存先が未接続なので、サイトの一覧には保存先未設定の案内が出ます。次の設定後に本番公開します。

## 3. 永続保存と送信キーを設定する

Vercelプロジェクトの **Storage** から **Blob** ストアを新規作成し、**Private** を選んで接続します。PreviewとProductionで学生の投稿を混ぜない場合は、それぞれ別のストアを使います。

現行SDKでは、接続済みプロジェクトの `BLOB_STORE_ID` とVercelのOIDCを利用できます。従来の `BLOB_READ_WRITE_TOKEN` を使う場合もサーバーの環境変数だけに設定します。このサイトはどちらも利用でき、Blobの認証情報を学生に配布する必要はありません。[Vercel公式のBlob接続・認証](https://vercel.com/docs/vercel-blob/using-blob-sdk)、[Private Blobの仕様](https://vercel.com/docs/vercel-blob/private-storage)

プロジェクトの **Settings → Environment Variables** に `THEME_SUBMIT_TOKEN` を設定します。空白を含まない24文字以上のランダムな値を使い、ゼミ生には別途案内します。プレビューと本番では別の送信キーを推奨します。`NEXT_PUBLIC_` などブラウザへ公開する変数名にはしません。

`THEME_STORAGE=local` と `THEME_LOCAL_DATA_DIR` はVercelに設定しません。Blobやキーが未設定の場合、投稿APIは503を返して受け付けません。

キーには投稿を追加する権限だけがあります。学生にVercel管理権限やBlobの読み書きトークンを渡しません。ゼミ共通キーなので、利用者ごとの認証や厳密な投稿数制限はありません。ゼミ内の少人数利用を想定した初期版です。

## 4. 本番公開とスキルの送信先を設定する

環境変数を設定したら再デプロイします。CLIの場合：

```bash
npx vercel --prod
```

取得した実際の本番URLを、スキルの `assets/site-config.json` に設定します。

```json
{ "site_url": "https://your-actual-project.vercel.app" }
```

例のURLをそのまま使わず、デプロイで確定したURLにします。このファイルはスキルにも同梱されるので、学生は送信キーを設定するだけで投稿できます。既にスキルを導入している学生には、更新を案内します。個人の `configure --site-url` または `THEME_SITE_URL` があれば、そちらが優先されます。

## 5. 公開後に確かめる

1. 投稿がないときに、空の一覧と共有方法が表示される。
2. スキルで選んだテーマをエクスポートし、本人が送信を依頼する。
3. ニックネーム、RQ、評価計画、未確認事項がサイトに表示される。
4. 同じJSONの再送は200となり、件数が増えない。
5. 別端末・再デプロイ後にも投稿が読める。
6. 送信キーなしのPOSTは401、不正形式は422となる。

共有JSONは64 KiB以内、1ページ50件です。読み込み済みのテーマを投稿日時で並べ、続きは「もっと読み込む」で取得します。Blobの料金・利用枠はVercelの契約と実際のアクセスに従うため、管理画面で確認してください。
