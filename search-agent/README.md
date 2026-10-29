# Search Agent - AI Agent による曖昧クエリ対応検索システム

## 概要

**「曖昧な指示」で「反復的に検索」できる**映画検索システム。

従来の検索システムでは、ユーザーは正確なキーワードを入力し、結果に満足できなければ最初からやり直す必要がありました。本システムは AI Agent を活用することで、以下を実現します：

### 曖昧なクエリへの対応
「なんとなくワクワクする映画」「心がほっこりする作品」といった感覚・雰囲気ベースの曖昧なクエリから、ユーザーの意図を汲み取って適切な映画を提示します。単純な全文検索やベクトル近似検索では拾えない「言語化しにくいニーズ」に対応。

### 反復的な検索（会話による絞り込み・拡張）
一度の検索で終わりではなく、**会話を通じて検索条件を段階的に調整**できます。「その中で〜」で絞り込み、「〜も見たい」で選択肢を広げ、「やっぱり違う」で条件を取り消す——自然な対話でユーザーが本当に求めている映画にたどり着けます。

### ユーザー嗜好の学習
検索履歴からユーザーの好みを学習し、パーソナライズされた検索結果を提供。使うほどに精度が向上します。

### 仕組み
検索は8フェーズのエージェントパイプラインで処理します。

会話意図分析 → クエリ構造化 → 嗜好取得 → DSL生成 → 検索 → 再ランキング → 回答生成 → 嗜好更新

各エージェントのシステムプロンプトは `backend/app/prompts/{エージェント名}/v{N}.md` でバージョン管理しています。詳細は [エージェント仕様](docs/SPECIFICATION.md) を参照してください。

## 会話型検索の例

### 絞り込み・拡張（継続表現あり）

```
ユーザー: 「アクション映画を探して」
AI: [アクション映画を10件表示]

ユーザー: 「その中でSFものを」          ← 「その中で」で継続を明示
AI: [アクション×SFの映画を表示]         ← 絞り込み（refine）

ユーザー: 「コメディも含めて」           ← 「〜も」で追加を明示
AI: [アクション×SF＋コメディの映画を表示] ← 条件拡張（expand）
```

### 暗黙的な新規検索（継続表現なし）

```
ユーザー: 「明るい映画」
AI: [明るい雰囲気の映画を10件表示]

ユーザー: 「盛り上がる映画」             ← 継続表現なし
AI: [盛り上がる映画を10件表示]          ← 新規検索（initial）
                                        ← 前回の「明るい」条件は引き継がない
```

**ポイント**: 「その中で」「〜も」などの継続表現がない場合、通常の検索窓への再入力と同様に新規検索として扱われます。

## クイックスタート

### 前提条件
- Docker / Docker Compose
- Google Cloud 認証情報（Vertex AI）
  - `gcloud auth application-default login` で `~/.config/gcloud/application_default_credentials.json` を作成しておく
  - 未作成のまま起動すると Docker が同名の空ディレクトリを作り、backend が起動しない
  - GCP プロジェクトは環境変数 `VERTEX_PROJECT_ID`（または `.env`）で指定

### 起動

```bash
# GCP 認証ファイルを作成（初回のみ）
gcloud auth application-default login

# リポジトリ直下から
cd search-agent

# コンテナ起動 + 映画データのインデックス作成
VERTEX_PROJECT_ID=<GCPプロジェクトID> make up
```

Makefile を使わない場合:

```bash
docker compose up -d
docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
```

http://localhost:3001 でフロントエンドにアクセスできます（`make help` で他のコマンドを確認できます）。

### 停止

```bash
make down
```

## API 使用例

### 検索

```bash
# 基本検索
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "なんとなくワクワクする映画", "session_id": "abc-123", "size": 10}'

# ユーザーID付き（嗜好学習あり）
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "アクション映画", "user_id": "user_001", "session_id": "abc-123", "size": 10}'

# 会話継続（同じsession_idで絞り込み）
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "その中でSFものを", "session_id": "abc-123", "size": 10}'
```

### ユーザー情報

```bash
# 嗜好取得
curl "http://localhost:8001/search/user/user_001/preference"

# 検索履歴取得
curl "http://localhost:8001/search/user/user_001/history"

# ユーザーデータ削除
curl -X DELETE "http://localhost:8001/search/user/user_001"
```

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [アーキテクチャ](docs/ARCHITECTURE.md) | 技術スタック、システム構成図、シーケンス図、ファイル構成 |
| [エージェント仕様](docs/SPECIFICATION.md) | 各エージェントの詳細仕様、Redisデータ構造 |
| [紹介スライド](docs/presentation.md) | システムの紹介（Marp。`make slides` で PDF 生成） |
| [フロントエンド](frontend/README.md) | フロントエンドの開発方法・機能 |

## 技術スタック

| コンポーネント | 技術 |
|--------------|------|
| バックエンド | FastAPI (Python) |
| フロントエンド | React 18 + TypeScript + Vite + Tailwind CSS |
| LLM | Claude (Vertex AI) |
| 検索エンジン | Elasticsearch 8.16.0 |
| 嗜好・会話の保存 | Redis 7.4.1 |
| コンテナ | Docker Compose |
| データ | TMDb 映画データ 約50,000件 |

## ポート

| サービス | ポート |
|---------|--------|
| Backend | 8001 |
| Frontend | 3001 |
| Elasticsearch | 9201 |
| Redis | 6380 |

## ディレクトリ構成

```
.                       # リポジトリ直下
├── search-agent/       # アプリケーション本体（このディレクトリ）
│   ├── backend/        # FastAPI + エージェント群（プロンプトは backend/app/prompts/）
│   ├── frontend/       # React フロントエンド
│   ├── docs/           # アーキテクチャ・仕様・紹介スライド
│   ├── docker-compose.yml
│   └── Makefile
├── data/               # TMDb 映画データ（CSV）
└── aqua.yaml           # 開発ツールのバージョン管理（gitleaks）
```

## データ

| ファイル | 内容 |
|---------|------|
| `data/tmdb_movies_50k.csv` | インデックス作成に使用する映画データ（約50,000件） |
| `data/tmdb_movies_data.csv` | 別形式の TMDb データ（現在のインデックス作成では未使用） |

`data/` はコンテナの `/data` にマウントされ、`backend/scripts/init_movies_index.py` が読み込みます。

## 開発ツール

[aqua](https://aquaproj.github.io/) で [gitleaks](https://github.com/gitleaks/gitleaks)（シークレット混入チェック）のバージョンを管理しています。リポジトリ直下で実行します。

```bash
aqua i
gitleaks git .
```
