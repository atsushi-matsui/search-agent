# Search Agent

AI エージェントによる、曖昧なクエリに対応した映画検索システム。

「なんとなくワクワクする映画」のような感覚的なクエリから意図を読み取り、「その中でSFものを」「コメディも見たい」と会話を重ねながら条件を絞り込み・拡張できます。検索履歴からユーザーの好みを学習し、結果をパーソナライズします。

## 構成

| コンポーネント | 技術 |
|--------------|------|
| フロントエンド | React 18 + TypeScript + Vite + Tailwind CSS |
| バックエンド | FastAPI (Python) |
| LLM | Claude（Vertex AI 経由） |
| 検索エンジン | Elasticsearch 8.16 |
| 嗜好・会話の保存 | Redis 7.4 |
| データ | TMDb 映画データ 約50,000件 |

検索は8フェーズのエージェントパイプラインで処理します（会話意図分析 → クエリ構造化 → 嗜好取得 → DSL生成 → 検索 → 再ランキング → 回答生成 → 嗜好更新）。詳細は [search-agent/README.md](search-agent/README.md) を参照してください。

## ディレクトリ構成

```
.
├── search-agent/       # アプリケーション本体
│   ├── backend/        # FastAPI + エージェント群（プロンプトは backend/app/prompts/）
│   ├── frontend/       # React フロントエンド
│   ├── docs/           # アーキテクチャ・仕様・紹介スライド
│   ├── docker-compose.yml
│   └── Makefile
├── data/               # TMDb 映画データ（CSV）
└── aqua.yaml           # 開発ツールのバージョン管理（gitleaks）
```

## クイックスタート

前提: Docker / Docker Compose、Vertex AI を利用できる Google Cloud 認証情報

```bash
# GCP 認証ファイルを作成（~/.config/gcloud/application_default_credentials.json）
gcloud auth application-default login

# 起動 + 映画データのインデックス作成
cd search-agent
VERTEX_PROJECT_ID=<GCPプロジェクトID> make up
```

起動後、http://localhost:3001 でフロントエンドにアクセスできます。

> 認証ファイルが無いまま起動すると、Docker が同名の空ディレクトリを作成して backend が起動しません。その場合はディレクトリを削除してから `gcloud auth application-default login` を実行してください。

| サービス | ポート |
|---------|--------|
| Frontend | 3001 |
| Backend (FastAPI) | 8001 |
| Elasticsearch | 9201 |
| Redis | 6380 |

停止は `make down`、その他のコマンドは `make help` で確認できます。

## データ

| ファイル | 内容 |
|---------|------|
| `data/tmdb_movies_50k.csv` | インデックス作成に使用する映画データ（約50,000件） |
| `data/tmdb_movies_data.csv` | 別形式の TMDb データ（現在のインデックス作成では未使用） |

`data/` はコンテナの `/data` にマウントされ、`search-agent/backend/scripts/init_movies_index.py` が読み込みます。

## ドキュメント

- [search-agent/README.md](search-agent/README.md) - システム概要・会話型検索の例・API 使用例
- [search-agent/docs/ARCHITECTURE.md](search-agent/docs/ARCHITECTURE.md) - システム構成・シーケンス・ファイル構成
- [search-agent/docs/SPECIFICATION.md](search-agent/docs/SPECIFICATION.md) - 各エージェントの仕様・Redis データ構造
- [search-agent/docs/presentation.md](search-agent/docs/presentation.md) - 紹介スライド（Marp）
- [search-agent/frontend/README.md](search-agent/frontend/README.md) - フロントエンド詳細

## 開発ツール

[aqua](https://aquaproj.github.io/) で [gitleaks](https://github.com/gitleaks/gitleaks)（シークレット混入チェック）のバージョンを管理しています。

```bash
aqua i
gitleaks git .
```
