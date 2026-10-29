# Search Agent Frontend

AI Agent による曖昧クエリ対応検索システムのフロントエンド。

## 技術スタック

- React 18.3.1
- TypeScript 7.0.2
- Vite 8.3.5
- Tailwind CSS 4.3.3（`@tailwindcss/postcss` 経由、テーマは `tailwind.config.js` を `@config` で読み込み）

## 開発環境

### 前提条件

- Node.js 20.19 以上（Vite 8 の要件）
- バックエンドが起動していること（`http://localhost:8001`）

### ローカル起動

```bash
npm install
npm run dev
```

http://localhost:3000 でアクセス可能。`/api` は `http://localhost:8001`（バックエンド）にプロキシされる。

### ビルド

```bash
npm run build
```

`dist/` ディレクトリに成果物が出力される。

## Docker

```bash
# コンテナビルド・起動
docker compose up -d --build frontend
```

http://localhost:3001 でアクセス可能。

## ディレクトリ構成

```
frontend/
├── src/
│   ├── api/
│   │   └── search.ts         # API呼び出し
│   ├── components/
│   │   ├── Header.tsx        # ヘッダー・ユーザーID切替
│   │   ├── HeroSection.tsx   # ヒーローセクション・検索エリア
│   │   ├── MovieCard.tsx     # 映画カード
│   │   ├── SearchBox.tsx     # 検索ボックス
│   │   └── SearchResults.tsx # 検索結果表示
│   ├── types/
│   │   └── search.ts         # 型定義
│   ├── App.tsx               # メインコンポーネント
│   ├── index.css             # グローバルスタイル
│   └── main.tsx              # エントリーポイント
├── Dockerfile
├── nginx.conf                # 本番用nginx設定
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## 機能

### 検索

- 曖昧なクエリ（「なんとなくワクワクする映画」など）で検索可能
- 検索例のサジェスト表示
- ローディング状態の表示
- 精密検索モードの ON/OFF（OFF 時は Rerank をスキップ。設定は localStorage に保存）
- 検索タイプの手動指定（自動 / 探索的 / 目的指向 / 比較。検証用）
- 会話による絞り込み・拡張（同一セッション内）と「セッションをクリア」

### ユーザー機能

- ユーザーID設定（ヘッダーから変更可能）
- ユーザーIDはlocalStorageに保存
- 検索履歴のサジェスト表示（ユーザーID設定時）

### 映画カード

- TMDbポスター画像表示（ない場合はプレースホルダー）
- ホバー時に詳細表示
  - タイトル・原題
  - ジャンルタグ（色分け）
  - 関連度スコア（プログレスバー）
  - AI による推薦理由
- 公式サイトリンク（homepageがある場合）

### 検索結果

- AI からのコメント表示
- 適用中の条件（累積した制約）の表示
- エージェント処理時間・処理ステップの折りたたみ表示

## API エンドポイント

フロントエンドは `/api/` プレフィックスでバックエンドにプロキシ。

| パス | メソッド | 説明 |
|------|----------|------|
| `/api/search` | POST | AI Agent 検索 |
| `/api/search/user/{user_id}/history` | GET | 検索履歴取得 |

## デザイン

- ライトテーマ（色トークン: `page` / `surface` / `surface-muted` / `brand`）
- レスポンシブ対応（2〜6列グリッド）
- ホバーアニメーション
- スケルトンローディング
