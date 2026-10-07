# theme-advice-skill

**自分の興味から、卒研で確かめたい問いを育てる。**

藤村ゼミの3年生が、AIとの対話で卒業研究のテーマを考えるためのCodexスキルです。趣味や日常の経験から発想を広げ、先行研究との違いを調べ、リサーチクエスチョンと評価方法を整理します。

AI活用、ブロックチェーン、電子価値取引など、ゼミの研究分野との接点を探します。メディアアートも扱います。テーマを選ぶのは学生本人で、先生との相談に使う提案書までまとめられます。

## どんな相談ができる？

- 研究したいことがまだ分からないので、興味を探したい。
- 思いついた案がありきたりに感じるので、違う切り口を考えたい。
- AIエージェントなど、新しく使える技術からテーマを考えたい。
- 先行研究との違いや、何を評価するかを整理したい。
- 前回の候補を見直したい。先生のコメントから考え直したい。

対話は **興味の探索 → 発想 → 候補の比較 → 先行研究の確認 → 評価計画 → 提案書** を目安に進みます。途中で戻ったり、関心のあるところから始めたりできます。

## Google Cloud Shellで使う

### 1. Cloud Shellを開く

[Google Cloud Shell](https://shell.cloud.google.com/) を開きます。ゼミ生は、ローカルに導入済みのCodexを **`npx codex`** で起動する前提です。Codexの再インストールやグローバルインストールは不要です。Python 3.9以上とGitを使います。スキルの補助スクリプトには追加のPythonパッケージは不要です。

### 2. スキルを導入する

GitHubの公開リポジトリから取得し、スキルを導入します。

```bash
cd ~
git clone https://github.com/kofujimura/theme-advice-skill.git
cd ~/theme-advice-skill
python3 scripts/install.py
```

スキルは `~/.agents/skills/theme-advice-skill/` に入ります。Codexの設定ファイルや、学生の検討記録は変更しません。[OpenAI公式のスキル配置・呼び出し方法](https://learn.chatgpt.com/docs/build-skills)

### 3. 自分の相談用フォルダでCodexを起動する

```bash
mkdir -p ~/graduation-theme
cd ~/graduation-theme
npx codex --search
```

`--search` は、最新の技術や先行研究を調べるためのWeb検索を有効にします。利用環境によって検索できない場合もあり、その場合は未確認事項と調査計画を残して相談を進めます。[OpenAI公式のWeb検索説明](https://learn.chatgpt.com/docs/web-search)

Codexの入力欄で `/skills` を入力し、`theme-advice-skill` が表示されることを確認します。見つからなければCodexを終了して、同じフォルダから起動し直してください。

### 4. 相談を始める

次の文章は **Codexの入力欄** に貼り付けてください。ターミナルのコマンドではありません。

```text
$theme-advice-skill
藤村ゼミの3年生です。卒研テーマを一緒に考えてください。
まだ研究したいことは決まっていません。
```

少し興味があることを添えても大丈夫です。

```text
$theme-advice-skill
推し活が好きです。自分の好みをAIに伝える難しさが気になっています。
この経験から卒研テーマを考えたいです。
```

AIの提案に対して「ここが面白い」「これは違う」「全部しっくりこない」と伝えてください。その理由が次の案を考える材料になります。分からない用語は、説明を求められます。

初回には、テーマを共有するときに表示する **ニックネーム** も聞きます。氏名や学籍番号は不要です。後から「ニックネームを○○に変更して」と伝えられます。

## 保存・再開する

通常は、最初の具体的な回答や、候補・調査の節目で、Codexが作業フォルダの `theme-workspace/` に要約を保存します。保存しない相談も可能です。

終了するときは、Codexに次のように伝えます。

```text
今日はここまでにします。今の候補と、次に考えることを保存してください。
```

次回は同じ作業フォルダで起動し、保存した記録から続けます。

```bash
cd ~/graduation-theme
npx codex --search
```

```text
$theme-advice-skill
theme-workspace の記録を読んで、前回の続きから相談したいです。
```

保存される主なファイルは次のとおりです。

| ファイル | 内容 |
| --- | --- |
| `session.json` | 興味、候補、出典、判断、未確認事項、次の作業 |
| `journal.md` | 検討の節目での短い振り返り |
| `snapshots/` | 段階が変わった時や終了時の記録のコピー |
| `candidate-comparison.md` | 候補の比較表。候補を絞った段階で作成 |
| `proposal.md` | テーマ提案書。草案の作成を依頼することも可能 |
| `theme.json` | 選んだテーマとニックネームの共有用JSON |
| `submission.json` | 送信の成否と、投稿の閲覧URL |
| `.send-config.json` | 送信先と送信キー。公開しない設定ファイル |

Cloud Shellでは、通常モードのホームディレクトリ内のファイルはセッションをまたいで保持されます。Ephemeral modeでは保持されません。大切な提案書は、自分のPCなどにも保存してください。[Google Cloud公式の保存仕様](https://docs.cloud.google.com/shell/docs/how-cloud-shell-works)

記録だけを確認する場合は、ターミナルから次を実行できます。

```bash
cd ~/graduation-theme
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py status
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py validate
```

`validate` は記録の形式や参照先IDを検査します。文献の真偽や、研究の新規性を判定する機能ではありません。

## 提案書を先生との相談に使う

```text
今の候補を比較表にしてください。
```

```text
候補C2を選びたいです。私が選んだ理由と、先行研究との差、
評価方法、最初の予備実験を含むテーマ提案書の草案を作ってください。
```

草案には、まだ調べていない部分も明記されます。AIが「新しい」と言っただけで新規性が確認されたことにはなりません。関連文献の内容を確かめ、自分が何を明らかにしたいのか説明できる形で先生に相談します。

## テーマを送って、みんなのアイデアを見る

### 最初に送信キーを設定する

送信先は [テーマ広場](https://theme-advice.vercel.app) にあらかじめ設定されています。ゼミの送信キーは先生から別途案内します。

以下は **ターミナル** の操作です。送信キーは非表示で入力し、Codexの対話には貼り付けません。

```bash
cd ~/graduation-theme
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py configure --prompt-token
```

設定は自分の `theme-workspace/` に保存され、スキルを更新しても保持されます。別のサイトへ変更する場合だけ、`configure --site-url <実際のHTTPS URL>` を使います。

### Codexで共有を頼む

```text
選んだテーマをJSONに保存してください。内容を確認してから共有したいです。
```

ニックネーム・問い・評価計画が `theme-workspace/theme.json` に保存されます。まだ調べていない点も、そのまま未確認として保存できます。

```text
このテーマを送る。
```

Codexが設定済みのサイトへJSONを送信し、成功したら閲覧URLを返します。サイトでは一覧、ニックネームや問いによる検索、新しさの切り口での絞り込み、テーマの詳細とJSONのダウンロードができます。投稿内容は、そのURLから閲覧できます。

共有するのは、選んだテーマの説明とニックネームです。対話全文、検討中の全候補、学籍番号、ローカル資料のパス、送信キーは共有JSONに含めません。自分の経験の説明や参考資料の要約も投稿されるので、内容を確認してから送ってください。

通信が途切れた場合は、成功とは表示しません。「同じテーマを再送して」と頼めます。同じID・同じ内容は重複投稿になりません。テーマを変更して再保存した場合は、新しい投稿になります。

ターミナルから使う場合：

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py export
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py send
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py status
```

詳しい形式と送信動作は [references/sharing.md](references/sharing.md) を参照してください。

## スキルを更新する

ソースのリポジトリから、明示的に更新します。

```bash
cd ~/theme-advice-skill
git pull --ff-only
python3 scripts/install.py --update
```

以前のスキルは、インストール先の隣にZIPで保存されます。学生の作業フォルダには触れません。新しいCodexセッションで更新後のスキルを使ってください。

## 教員・開発者向け

指導の設計と、教育研究での試行方法は [docs/design.md](docs/design.md) にまとめています。研究室の方針や参考資料は [references/seminar-context.md](references/seminar-context.md) で更新できます。

検討の要約はローカルに保存し、共有は学生の「テーマを送る」という依頼で行います。教育研究として対話の記録を収集する場合は、共有範囲や手続きを別途定めます。このスキルの要約保存とは別に、Codex自体は会話履歴を持ち、対話内容は利用するAIサービスに送られます。

**テーマ共有サイト** もこのリポジトリに含みます。新しいVercelプロジェクトとして公開する手順は [docs/site-setup.md](docs/site-setup.md) にまとめています。サイトはHTML/CSS/JavaScript、投稿APIはVercel Functions、永続保存はPrivate Vercel Blobです。学生側のスキルにNode.jsパッケージの追加導入は不要です。

```text
theme-advice-skill/
├── SKILL.md                     対話の進め方
├── VERSION                      スキルの版
├── agents/openai.yaml           Codexでの表示名
├── references/                  指導・発想・調査・記録の指針
├── assets/                      記録と提案書のテンプレート
├── scripts/install.py           導入・更新（Python標準ライブラリのみ）
├── scripts/workspace.py         初期化・整合性確認・チェックポイント
├── scripts/share.py             ニックネーム・JSON保存・テーマ送信
├── web/                         テーマ共有サイトの画面
├── api/                         Vercelの投稿・閲覧API
├── lib/                         JSON検証と永続保存
├── vercel.json                  Vercelの設定
├── docs/design.md               設計と試行の観点
└── tests/                       保存・導入・投稿の動作検査
```

補助スクリプトの検査：

```bash
python3 -m unittest discover -s tests -v
npm ci
npm test
npm run build
```

CLIと導入手順の公式情報は2026-10-07に確認しました。Google Cloud Shell上での実利用は、学生のアカウントで導入・検索・再開を試して確認してください。
