# 保存・再開の記録形式（schema 1.0）

保存先は、学生の作業ディレクトリ配下の `theme-workspace/`。スキルのインストール先に学生の記録を置かない。ホームディレクトリ内の作業場所を推奨する。指定があれば、その場所を使う。

## 保存するファイル

- `session.json`：再開に必要な構造化記録。以下の形式で更新する。
- `journal.md`：日時・段階・分かったこと・本人の判断・未確認事項・次の作業の短い記録。会話全文は転記しない。
- `snapshots/session-*.json`：段階の変更時や終了時の記録のコピー。`checkpoint` コマンドで作る。
- `candidate-comparison.md`：候補を絞った時点の読みやすい比較表。候補IDをJSONと揃える。
- `proposal.md`：本人が選んだ候補の提案書。草案の不足を明記する。
- `theme.json`：本人が選んだテーマとニックネームの共有用JSON。[共有手順](sharing.md) を参照。
- `.send-config.json`：送信先と送信キー。非公開のローカル設定で、検討記録や共有JSONにはコピーしない。
- `submission.json`：最後の送信の成否と閲覧URL。キーを含めない。
- `shared-themes/`：変更前の共有JSON。再送時のIDを追跡できる。

ファイル操作できない場合は、同じ内容を会話で返し、保存したとは言わない。既存JSONが壊れている場合は消去・再初期化せず、読める部分を確認して修復する。

## 初期化・確認・チェックポイント

パスはインストールされたスキルの `SKILL.md` の位置から解決する。学生が自分で実行する場合の例：

```bash
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py init --workspace theme-workspace
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py validate --workspace theme-workspace
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py checkpoint --workspace theme-workspace
python3 ~/.agents/skills/theme-advice-skill/scripts/workspace.py status --workspace theme-workspace
```

`init` は既存のJSON・日誌を保持し、不足する初期ファイルだけを作る。`checkpoint` は整合性を確認し、`updated_at` を現在のUTC日時に更新して、重複しない名前のコピーを作る。提案書の未記入項目を自動的に埋める機能ではない。日誌はCodexが対話から追記する。

## session.json

基本形は [session.template.json](../assets/session.template.json)。時刻はタイムゾーン付きISO 8601形式。日時は実際の時計で取得する。

| フィールド | 値・意味 |
| --- | --- |
| `schema_version` | `"1.0"` |
| `skill_version` | 記録を更新したスキルの `VERSION` の値。過去の版はスナップショットに残る |
| `created_at`, `updated_at` | UTC等のタイムゾーン付き日時 |
| `stage` | `explore`, `diverge`, `focus`, `investigate`, `plan`, `proposal` |
| `environment.model` | 実際に確認できたモデル名、分からなければ `null` |
| `environment.codex_version` | `npx codex --version` 等で確認した値、分からなければ `null` |
| `environment.search` | `unknown`, `available`, `unavailable`。実際の利用結果から更新 |
| `student.participant_id` | 教員・学生が指定した仮名ID、指定がなければ `null`。氏名・学籍番号を代入しない |
| `student.nickname` | 初回の対話で本人に聞く、共有時に表示する1〜40文字のニックネーム。共有しない間は `null` 可。旧記録では省略可 |
| `student.interests`, `experiences`, `constraints` | 下記の観察オブジェクトの配列 |
| `student.own_words` | 本人が述べた問い・選択理由・説明の短い引用の配列。AIによる代筆を本人の発言にしない |
| `candidates` | 下記の候補オブジェクトの配列。IDは再利用しない |
| `selected_candidate_id` | 本人が選んだ候補ID、未選択なら `null` |
| `sources` | 下記の資料オブジェクトの配列 |
| `searches` | 調査日時 `at`、検索語 `query`、検索場所・資料の範囲 `scope`、限界 `limitations` を文字列で持つ配列 |
| `decisions` | 下記の判断イベントの配列。新しい判断を追記し、過去を黙って書き換えない |
| `next_actions` | 次に確かめることの文字列配列 |

### 観察オブジェクト

```json
{"text": "自分の好みを他人に説明するのが難しい", "origin": "student", "confirmed_by_student": true}
```

`origin` は `student` または `assistant`。AIの解釈は `assistant` として、本人が確認するまで `confirmed_by_student: false` にする。本人が訂正した観察は現状に更新し、変更理由を日誌・判断イベントに残す。

### 候補オブジェクト

空の値は検討中を表す。検討初期の候補でもこの基本形を使い、未確認の内容を埋めない。

```json
{
  "id": "C1",
  "title": "AI代行に伝える譲れない条件",
  "interest_connection": "本人の推し活での選択経験との接点。本人の確認はこれから",
  "rq": "条件の伝え方は、模擬購入課題での条件違反にどう影響するか？",
  "contribution_types": ["problem"],
  "novelty_status": "unverified",
  "novelty_claim": "意図が変化する場面の問題を調べる候補。先行研究との差は未確認",
  "source_ids": [],
  "technology": {
    "capability": "条件付きの行動を代行するAI",
    "availability": "unverified",
    "source_ids": [],
    "conditions": "利用環境・費用・モデルは未確認"
  },
  "evaluation": {
    "comparison": "",
    "metrics": [],
    "procedure": "",
    "resources": "",
    "limitations": ""
  },
  "pilot": "",
  "student_feedback": [],
  "readiness": {
    "interest": "unknown",
    "question": "needs_work",
    "novelty": "unknown",
    "evaluation": "unknown",
    "feasibility": "unknown",
    "ownership": "unknown"
  },
  "open_questions": ["本人が気になるか", "最も近い研究は何か"]
}
```

`contribution_types` は `technical`, `application`, `problem`, `artistic` の配列。`novelty_status` は調査指針の3値。`technology.availability` は `unverified`, `verified`, `unavailable`。`student_feedback` は本人の短い発言の文字列配列。`readiness` は調査指針の6軸で、各値は `ready`, `needs_work`, `unknown`。

`search_scoped` には、実際に読んだ資料IDを少なくとも一つ付ける。`teacher_reviewed` には教員の実際のコメントを判断イベントに残す。`technology.availability: verified` には実際に読んだ根拠資料IDを付ける。JSONが整合していることと、根拠が学術的に十分なことは別。

### 資料オブジェクト

```json
{
  "id": "S1",
  "kind": "lab",
  "title": "資料の実際のタイトル",
  "url": "https://web.fujimura.com/",
  "read_level": "full_text",
  "checked_at": "2026-10-07T01:00:00+00:00",
  "takeaway": "実際に読んだ内容と、その資料が支える主張の範囲"
}
```

`kind` は `paper`, `official`, `lab`, `artwork`, `other`。`read_level` は `full_text`, `abstract`, `snippet`, `unread`。URLはHTTP(S)の実際のリンク。ローカル資料の場合は `file` にパスを記録し `url: null` とする。`checked_at` は未読なら `null` でもよい。例の日時や資料を、実際の調査記録としてコピーしない。

### 判断イベント

```json
{
  "at": "2026-10-07T01:00:00+00:00",
  "actor": "student",
  "action": "select",
  "candidate_id": "C1",
  "reason": "本人が自分の経験とつながると述べ、この候補を選んだ",
  "student_quote": "これを調べてみたいです"
}
```

`actor` は `student`, `assistant`, `teacher`。`action` は `propose`, `revise`, `select`, `reject`, `reopen`, `teacher_feedback`。`candidate_id` と `student_quote` は該当しなければ `null`。AIの推薦は `assistant/propose`。本人の選択は `student/select` とする。

## 教育研究での利用

ローカルに検討の要約と版を残す機能であり、収集への同意や匿名化の完了を示すものではない。経験の自由記述から個人が推測される可能性もある。研究目的の共有範囲・手続きは教員が別に決め、共有する際は本人が対象を確認する。自動アップロードはしない。

比較や評価に使う場合は、採用した候補だけでなく、変更・却下の理由と本人の説明を見られる。Codexの内部の推論や会話全文の収集機能は実装しない。
