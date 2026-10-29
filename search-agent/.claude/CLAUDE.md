# Search Agent プロジェクト

AI Agent による曖昧クエリ対応映画検索システム。

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **フロントエンド**: React 18 + TypeScript + Vite + Tailwind CSS
- **LLM**: Claude (Vertex AI経由)
- **検索エンジン**: Elasticsearch 8.16.0
- **キャッシュ**: Redis 7.4.1
- **コンテナ**: Docker Compose

## 起動・停止

前提: Vertex AI 用の GCP 認証ファイルが必要（`gcloud auth application-default login` で `~/.config/gcloud/application_default_credentials.json` を作成）。
ファイルが無いまま起動すると Docker が同名の空ディレクトリを作り、backend が起動しない。

```bash
# 起動 + 映画データ投入（Makefile）
make up

# 起動のみ
docker compose up -d

# 停止
docker compose down

# ログ確認
docker compose logs backend -f
docker compose logs frontend -f
```

## 開発時の操作

### バックエンド修正後

```bash
docker compose restart backend
```

### フロントエンド修正後

```bash
docker compose up -d --build frontend
```

### 映画インデックス再作成

```bash
docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
```

## ポート

| サービス | ポート |
|---------|--------|
| Backend (FastAPI) | 8001 |
| Frontend (React) | 3001 |
| Elasticsearch | 9201 |
| Redis | 6380 |

## アーキテクチャ

### 8フェーズのエージェントパイプライン

1. **ConversationAnalyzerAgent** - 会話意図を分析（継続/絞り込み/拡張）
2. **QueryUnderstandingAgent** - 曖昧クエリを構造化
3. **UserPreferenceAgent** - Redis からユーザー嗜好取得
4. **QueryToESAgent** - Elasticsearch DSL 生成（統合エージェント）
5. **RetrievalAgent** - ES 検索実行
6. **RerankAgent** - LLM + ES スコアで再ランキング（精密検索モード）
7. **AnswerAgent** - ユーザー向け説明生成（目的指向検索ではスキップ）
8. **PreferenceUpdaterAgent** - ユーザー嗜好を Redis に更新

### Rerank Agent のスコア統合

```
最終スコア = 0.3 × 正規化(ES) + 0.7 × 正規化(LLM)
```

- ES_WEIGHT は `backend/app/agents/rerank.py` で定義
- 両スコアは Min-Max 正規化で [0, 1] に統一

### プロンプト管理

各エージェントのシステムプロンプトは `backend/app/prompts/{プロンプト名}/v{N}.md` で管理する（ローダー: `backend/app/core/prompt.py`）。

- 変更時は既存ファイルを直接編集せず、`v2.md` のように新バージョンを追加する
- デフォルトは最新バージョンを使用。`PROMPT_VERSION_CONFIG` で固定可能（例: `"rerank:v1,query_to_es:v2"`）
- プレースホルダは `$name` 形式（`string.Template`）。JSON 例の `{ }` はエスケープ不要
- プロンプトは起動時に読み込むため、変更後は `docker compose restart backend` が必要

## 主要ファイル

### バックエンド

| パス | 説明 |
|------|------|
| `backend/app/agents/orchestrator.py` | エージェント統括 |
| `backend/app/agents/rerank.py` | 再ランキング（スコア統合） |
| `backend/app/core/llm.py` | Claude API クライアント |
| `backend/app/core/prompt.py` | プロンプトローダー |
| `backend/app/prompts/` | 各エージェントのシステムプロンプト |
| `backend/app/core/redis.py` | Redis クライアント |
| `backend/app/api/search.py` | 検索 API エンドポイント |

### フロントエンド

| パス | 説明 |
|------|------|
| `frontend/src/App.tsx` | メインコンポーネント |
| `frontend/src/components/MovieCard.tsx` | 映画カード |
| `frontend/src/components/SearchBox.tsx` | 検索ボックス |
| `frontend/src/api/search.ts` | API クライアント |

## API テスト

```bash
# 基本検索
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "なんとなくワクワクする映画", "size": 5}'

# ユーザーID付き（嗜好学習あり）
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "アクション映画", "user_id": "user_001", "size": 5}'

# ユーザー嗜好取得
curl http://localhost:8001/search/user/user_001/preference
```

## ドキュメント

- `README.md` - システム全体の概要
- `docs/ARCHITECTURE.md` - システム構成・シーケンス・ファイル構成
- `docs/SPECIFICATION.md` - 各エージェントの仕様、Redis データ構造
- `docs/presentation.md` - 紹介スライド（Marp。`make slides` で PDF 生成）
- `frontend/README.md` - フロントエンド詳細

## 注意事項

- バックエンドのコード変更後は `docker compose restart backend` が必要
- LLM 呼び出し回数（1検索あたり）: 高速モード 4回、精密検索モード 5回、目的指向検索 2回。user_id ありの場合は嗜好更新で +1回（非同期）
- 映画データは TMDb からインポート（約 50,000 件）
