# ニックネームとテーマの共有

パスは、読み込んだ `SKILL.md` のディレクトリから解決する。以下は学生によるターミナル実行例。Codexは実際のインストール先に置き換える。

## 初回の設定

ニックネームは初回の対話で本人に聞く。既存の記録にない場合も相談は続け、送信前には必ず本人に設定してもらう。

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py nickname "本人が指定したニックネーム"
```

送信先は配布されたスキルの `assets/site-config.json` の `site_url`。未設定なら先生から案内されたURLを設定する。推測した `.vercel.app` URLには送らない。URLと送信キーを設定する例：

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py configure --site-url "$THEME_SITE_URL"
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py configure --prompt-token
```

`THEME_SITE_URL` には先生から案内された実際のHTTPS URLを設定して使う。送信キーは学生本人がターミナルで非表示入力する。Codexに貼り付けさせない。設定は作業フォルダの `theme-workspace/.send-config.json` に読み書き権限600で保存する。送信キーは `THEME_SUBMIT_TOKEN`、送信先は `THEME_SITE_URL` でも指定でき、環境変数が優先される。設定の確認は `share.py status`。キーの値を表示しない。更新で個人の送信設定は消えない。

## 共有用JSONを作る

`session.json` は本人の検討用。`theme.json` は [共有スキーマ](../assets/public-theme.schema.json) に沿った外部送信用で、形式の版は1.0。

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py validate
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py export
```

選択した候補から次を保存する：ニックネーム、タイトル、RQ、興味との接点、新しさの種類と仮説・調査段階、利用技術と条件、比較・指標・評価手順・資源・限界、予備実験、未確認事項、関連資料。ローカル資料は書誌情報のみで、ファイルパスを含めない。資料の参照IDを保持する。日誌、対話全文、全候補、participant_id、モデル情報、readiness、本人の発言の記録、設定・送信キーは含めない。

本人が選択した判断イベントとニックネームが必要。タイトルとRQは空にできない。未調査の新規性は未確認のまま送り、調査済みを装わない。完全な研究計画や教員の承認を共有の必須条件にはしない。

内容が変わらない再保存ではIDと作成日時を維持する。内容が変わったら新しいIDになり、以前のJSONは `shared-themes/` に残る。公開済み投稿の上書き・削除を自動では行わない。

## 「テーマを送る」を実行する

1. 対話で学生が明示的に共有を依頼したことを確認する。
2. 候補を勝手に選ばず、記録を検証し共有JSONを作る。
3. ニックネーム、タイトル、RQ、送信先、JSONの保存先を知らせる。このURLから投稿内容を閲覧できることは、初回共有時に説明する。
4. 次を実行し、応答を確認する。

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/share.py send
```

`send` は、既に保存した `theme.json` をHTTPSの `/api/themes` に送る。成功なら `submission.json` に `sent` と閲覧URLを残す。同じID・同じ内容は重複投稿にならない。異なる内容で同じIDを使うと409になり、既存投稿を保持する。

キー未設定では、非表示入力の設定コマンドを案内して待つ。タイムアウトや接続失敗は `unknown` として記録する。送信成功を推測しない。「テーマを再送」と頼まれたときは、既存 `theme.json` のまま再送する。再エクスポートやIDの再作成はしない。503ならサイト側のBlob接続・キー設定の確認も必要。

別の保存先なら、例の `share.py` の直後に `--workspace <保存先>` を指定する。HTTPのlocalhostは開発検査に限り `--allow-local-http` が必要。サイトへの投稿と、教育研究目的の対話記録の収集は別の手続きである。
