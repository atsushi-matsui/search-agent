# エージェント仕様書

## エージェント一覧

| Phase | Agent名 | 処理方式 | 目的 | 入力 | 出力 |
|-------|---------|---------|------|------|------|
| 0 | Session Management | ルールベース | セッション管理 | session_id, user_id | ConversationContext |
| 1 | Conversation Analyzer | **LLM** | 会話意図判定 | query, 会話履歴 | ConversationIntent |
| 2 | Query Understanding | **LLM** | クエリ構造化 | query | StructuredQuery |
| 3 | User Preference | ルールベース | 嗜好取得 | user_id | UserPreferenceData \| None |
| 4 | Query to ES | **LLM** + ルール | DSL生成・マージ | StructuredQuery, UserPreference, constraints | ElasticsearchDSL |
| 5 | Retrieval | ルールベース | ES検索実行 | ElasticsearchDSL | Movie[] |
| 6 | Rerank | **LLM** + ルール | 再ランキング（精密検索モード） | Movie[], StructuredQuery, UserPreferenceData | RankedMovie[] |
| 7 | Answer | **LLM** | 回答生成（目的指向検索ではスキップ） | RankedMovie[], StructuredQuery | 説明文 |
| 8 | Preference Updater | **LLM** | 嗜好更新（非同期） | user_id, StructuredQuery, RankedMovie[] | UserPreferenceData |

各エージェントのシステムプロンプトは `backend/app/prompts/{エージェント名}/v{N}.md` で管理し、`backend/app/core/prompt.py` で読み込む。

---

## Phase 0: Session Management（ルールベース）

**目的**: Redis からセッションコンテキストを取得/作成

**処理内容**:
1. `session:context:{user_id}:{session_id}` キーで Redis を検索
2. 存在すれば既存コンテキストを使用、なければ新規作成
3. TTL: 30分

**入出力**:
- 入力: `session_id`, `user_id`
- 出力: `ConversationContext` (turns, current_constraints)

---

## Phase 1: Conversation Analyzer Agent（LLM）

**目的**: ユーザーの発言から会話の意図を判定（複合型インテント対応）

**処理内容**:
1. 会話履歴がない場合も LLM を呼び出し、actions と search_behavior を判定する（is_continuation は常に false）
2. 履歴がある場合、LLM に以下を渡して意図を分析：
   - 過去の発言履歴（最大5件）
   - 現在の制約条件
   - 今回のクエリ
3. **1つの発言に複数の意図が含まれる場合、actions配列として順番に返却**

**アクションタイプ**:

| タイプ | 説明 | 判定例 | ESクエリへの影響 |
|--------|------|--------|-----------------|
| `initial` | 新規検索 | 「アクション映画を探して」「盛り上がる映画」 | 新規DSL生成 |
| `refine` | 絞り込み（AND条件） | 「その中でSFものを」「〜に絞って」 | filter句にAND条件追加 |
| `expand` | 選択肢拡張（OR条件） | 「コメディも含めて」「〜も見たい」 | should句にOR条件追加 |
| `undo` | 直前取り消し | 「やっぱり違う」「今のなし」 | 直前ターンを取り消し |
| `reset_all` | 全履歴クリア | 「最初から」「リセット」 | セッション全体をクリア |

**initial vs refine/expand の判定基準**:

- `refine`/`expand` は「明示的に継続を示す表現」がある場合のみ適用
- 継続表現なしに新しい条件を提示した場合は `initial`（通常の検索窓への再入力に相当）

| ケース | 判定 | 理由 |
|--------|------|------|
| 「明るい映画」→「盛り上がる映画」 | `initial` | 継続表現なし、別の検索軸 |
| 「アクション映画」→「コメディ映画」 | `initial` | 継続表現なし、別ジャンル |
| 「アクション映画」→「その中でSF」 | `refine` | 「その中で」で継続を明示 |
| 「アクション映画」→「SFもいいな」 | `expand` | 「〜もいい」で追加を明示 |

**複合型インテントの例**:

| パターン | 入力例 | 出力actions |
|---------|--------|-------------|
| undo + refine | 「やっぱ、年代の新しい作品がいい」 | `[undo, refine:['年代:新しい']]` |
| refine + expand | 「新しめで、アニメも見たい」 | `[refine:['年代:新しめ'], expand:['ジャンル:アニメ']]` |
| reset_all + initial | 「やめた、ホラー映画が見たい」 | `[reset_all, initial:['ジャンル:ホラー']]` |

**検索行動タイプ (search_behavior)**:

| タイプ | 説明 | 判定例 | 処理方式 |
|--------|------|--------|---------|
| `exploratory` | 探索的検索 | 「アクション映画」「ワクワクする映画」 | LLM曖昧検索（フル） |
| `goal_oriented` | 目的指向検索 | 「インセプションが見たい」「トム・ハンクスの映画」 | 全文検索（LLMスキップ） |
| `comparative` | 比較検索 | 「AとBどっちがいい？」 | LLM曖昧検索（比較重視） |

- **exploratory**: ジャンル、気分、条件など曖昧な条件での検索。LLMで意図を補完する。
- **goal_oriented**: 特定のタイトル名や人物名など固有名詞を指定した検索。全文検索で十分。
- **comparative**: 複数の選択肢を比較する検索。LLMで比較を支援する。

**入出力**:
- 入力: `query`, `ConversationContext`
- 出力: `ConversationIntent` (actions: IntentAction[], is_continuation, reasoning, search_behavior)

---

## Phase 2: Query Understanding Agent（LLM）

**目的**: 曖昧なユーザークエリを構造化された情報に変換

**処理内容**:
Few-shot プロンプトで LLM に以下を抽出させる：
- `english_query`: クエリの英訳（目的指向検索の全文検索に使用）
- `intent`: ユーザーの検索意図の言語化
- `genres`: 関連するジャンル（例: ["アクション", "SF"]）
- `mood_tags`: 雰囲気タグ（例: ["ワクワク", "爽快"]）
- `keywords`: 重要なキーワード
- `time_period`: 時代設定（あれば）
- `target_audience`: ターゲット層（あれば）

**Few-shot例**:
```
Input: "なんとなくワクワクする映画"
Output:
{
  "intent": "気分が高揚するような刺激的な映画を探している",
  "genres": ["アクション", "アドベンチャー", "SF"],
  "mood_tags": ["ワクワク", "爽快", "スリリング"]
}
```

**入出力**:
- 入力: `query` (文字列)
- 出力: `StructuredQuery`

---

## Phase 3: User Preference Agent（ルールベース）

**目的**: Redis に蓄積されたユーザー嗜好を取得し、後続フェーズに渡す

**処理内容**:
1. `user_id` がなければ `None` を返却
2. Redis（`user:preference:{user_id}`）から嗜好データを取得
3. データがなければ `None` を返却（初回ユーザー。後続は嗜好なしとして処理）

LLM は呼び出さない。嗜好の生成・更新は Phase 8 が担当する。

**入出力**:
- 入力: `user_id`
- 出力: `UserPreferenceData | None` (preferred_genres, genre_weights, mood_preferences, boost_conditions など)

---

## Phase 4: Query to ES Agent（LLM + ルールベース）

**目的**: 構造化クエリとユーザー嗜好から Elasticsearch DSL を生成

**search_behavior による分岐**:

| search_behavior | 処理方式 | DSL生成 |
|-----------------|---------|---------|
| `exploratory` | LLM | スキーマ情報を基にLLMがDSLを生成 |
| `goal_oriented` | ルールベース | 英訳クエリ（なければ原文）で全フィールド検索（`multi_match`, `fields: ["*"]`） |
| `comparative` | LLM | exploratoryと同様 |

**処理内容（exploratory/comparative）**:
1. ES からインデックスのマッピング情報を取得
2. LLM にスキーマ情報・StructuredQuery を渡し、DSL を直接生成させる
3. **ルールベースのマージ処理**（refine/expand制約を分離して適用）:
   - `refine_constraints`: 前回 DSL の `filter` 句に AND 条件として追加
   - `expand_constraints`: 前回 DSL の `should` 句に OR 条件として追加

**処理内容（goal_oriented）**:
1. `english_query`（なければ原文）を全フィールド検索に使用
2. LLM呼び出しなし（高速化）

**DSLマージロジック**:
- `refine`: 新規条件群を「少なくとも1つを満たす」形にまとめてから、前回DSLにAND条件として追加
- `expand`: 新規条件を前回DSLのshould句にOR条件として追加
- **複合パターン**: refine + expand が同時にある場合、それぞれ適切な句に追加

**ユーザー嗜好のブースト適用**:
- `boost_conditions`: `function_score`の`filter`+`weight`形式でスコアブースト
- ブーストはマッチングには影響せず、スコアリングのみに適用

**入出力**:
- 入力: `StructuredQuery`, `UserPreferenceData`, `refine_constraints`, `expand_constraints`, `previous_dsl`, `search_behavior`
- 出力: `ElasticsearchDSL` (query, sort, size=20)

---

## Phase 5: Retrieval Agent（ルールベース）

**目的**: Elasticsearch から検索結果を取得

**処理内容**:
1. DSL を Elasticsearch に送信
2. ヒットしたドキュメントを Movie オブジェクトに変換
3. 20件を取得（Rerank 用の候補）

**入出力**:
- 入力: `ElasticsearchDSL`
- 出力: `Movie[]` (最大20件)

---

## Phase 6: Rerank Agent（LLM + ルールベース）- 精密検索モード

**目的**: 検索結果をユーザーの意図と嗜好に基づいて再ランキング

**注**: 精密検索モードのみ実行。高速モードではスキップされる。

**処理内容**:
1. 上位 10 件（`MAX_RERANK_MOVIES`）を LLM に渡し、意図・嗜好に基づく関連性スコアと順位を判定させる（結果も最大 10 件）
2. **ルールベースのスコア統合**:
   - ES スコアと LLM スコアを正規化（0-1）
   - 最終スコア = 0.3 × ES + 0.7 × LLM

**スコア統合式**:
```python
final_score = 0.3 * normalized_es_score + 0.7 * normalized_llm_score
```

**入出力**:
- 入力: `Movie[]`, `StructuredQuery`, `UserPreferenceData`
- 出力: `RankedMovie[]` (rank, relevance_score, es_score, llm_score, explanation)

---

## Phase 7: Answer Agent（LLM）

**目的**: ユーザー向けの説明文を生成

**注**: 高速・精密どちらのモードでも実行する。目的指向検索（goal_oriented）ではスキップされる。

**処理内容**:
1. 検索結果がなければ定型メッセージを返却
2. 上位5件の映画と意図を LLM に渡し、説明文を生成

**入出力**:
- 入力: `RankedMovie[]`, `StructuredQuery`
- 出力: `string` (2-3文の説明文)

---

## Phase 8: Preference Updater Agent（LLM）

**目的**: 検索結果に基づいてユーザー嗜好を更新

**処理内容**:
1. `user_id` がなければスキップ
2. 検索レスポンスを待たずにバックグラウンド（ThreadPoolExecutor）で実行
3. 現在の嗜好・直近10件の検索履歴・今回の検索結果を LLM に渡し、更新された嗜好を生成
4. Redis に保存

**更新ルール**:
- 新しい検索結果のジャンルを既存嗜好に統合
- 頻出ジャンルの重みを増加（最大1.0）
- 急激な変化は避け、古い嗜好も維持

**boost_conditionsで使用可能なフィールド**:
- `genres`: keyword配列（英語ジャンル名）
- `overview`: text（英語キーワード）

**入出力**:
- 入力: `user_id`, `StructuredQuery`, `RankedMovie[]`
- 出力: `UserPreferenceData` (preferred_genres, genre_weights, mood_preferences, boost_conditions)

---

## Redis データ構造

### ユーザー嗜好 (`user:preference:{user_id}`)

```json
{
  "user_id": "user_001",
  "preferred_genres": ["Adventure", "Action", "Comedy"],
  "genre_weights": {"Adventure": 0.9, "Action": 0.7, "Comedy": 0.6},
  "mood_preferences": ["ワクワク", "爽快", "スリリング"],
  "recent_search_themes": ["気分高揚", "刺激的"],
  "boost_conditions": [
    {"field": "genres", "values": ["Action", "Adventure"], "boost": 1.8},
    {"field": "overview", "values": ["exciting", "thrilling"], "boost": 1.3}
  ],
  "created_at": "2025-12-01T06:05:08.238992",
  "updated_at": "2025-12-01T06:05:08.239079"
}
```

### 検索履歴 (`user:query_history:{user_id}`)

```json
[
  {
    "id": "5b1c2d3e-...",
    "query": "なんとなくワクワクする映画",
    "result_movie_ids": ["14160", "9543", "9593"],
    "timestamp": "2025-12-01T06:05:05.488723"
  }
]
```

### 会話コンテキスト (`session:context:{user_id}:{session_id}`)

セッション単位で会話履歴と累積制約を管理。TTL: 30分
各ターンには嗜好スナップショットが保存され、undo/reset_all時に復元可能。

```json
{
  "session_id": "abc-123-def-456",
  "user_id": "user_001",
  "turns": [
    {
      "query": "アクション映画",
      "intent_type": "initial",
      "constraints": ["ジャンル:アクション"],
      "result_movie_ids": ["14160", "9543"],
      "es_dsl": {"query": {...}, "sort": [...], "size": 20},
      "preference_snapshot": {"preference": {...}},
      "query_history_id": "abc-123",
      "timestamp": "2025-12-04T10:00:00"
    },
    {
      "query": "その中でSFものを",
      "intent_type": "refine",
      "constraints": ["ジャンル:アクション", "ジャンル:SF"],
      "result_movie_ids": ["27205", "603"],
      "es_dsl": {"query": {...}, "sort": [...], "size": 20},
      "preference_snapshot": {"preference": {...}},
      "query_history_id": "def-456",
      "timestamp": "2025-12-04T10:01:00"
    }
  ],
  "current_constraints": ["ジャンル:アクション", "ジャンル:SF"],
  "created_at": "2025-12-04T10:00:00",
  "updated_at": "2025-12-04T10:01:00"
}
```
