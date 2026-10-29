.PHONY: up down start stop restart-backend restart-frontend restart logs logs-backend logs-frontend init reindex clear-redis reset-data clean rebuild slides slides-html help

# アプリ起動 + データ初期化
up:
	docker compose up -d
	@echo "Waiting for Elasticsearch to be ready..."
	@sleep 10
	docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
	@echo "✅ Application started and data initialized"

# アプリ終了
down:
	docker compose down
	@echo "✅ Application stopped"

# アプリ起動のみ（データ初期化なし）
start:
	docker compose up -d
	@echo "✅ Application started"

# アプリ停止（コンテナ保持）
stop:
	docker compose stop
	@echo "✅ Application stopped (containers preserved)"

# バックエンド再起動
restart-backend:
	docker compose restart backend
	@echo "✅ Backend restarted"

# フロントエンド再ビルド
restart-frontend:
	docker compose up -d --build frontend
	@echo "✅ Frontend rebuilt"

# 全サービス再起動
restart:
	docker compose restart
	@echo "✅ All services restarted"

# ログ表示
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

# データ初期化のみ
init:
	docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
	@echo "✅ Movie index initialized"

# データ再登録（インデックス削除 → 再作成）
reindex:
	docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
	@echo "✅ Movie index recreated"

# Redisデータクリア
clear-redis:
	docker compose exec redis redis-cli FLUSHALL
	@echo "✅ Redis data cleared"

# 全データリセット（ES + Redis）
reset-data:
	docker compose exec redis redis-cli FLUSHALL
	docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
	@echo "✅ All data reset (ES + Redis)"

# ボリューム含めて完全クリーンアップ
clean:
	docker compose down -v
	@echo "✅ Application stopped and volumes removed"

# 再ビルド + 起動 + データ初期化
rebuild:
	docker compose down
	docker compose up -d --build
	@sleep 10
	docker compose exec backend python /app/scripts/init_movies_index.py --force-recreate
	@echo "✅ Application rebuilt and data initialized"

# スライドをPDFに変換
# 使用例: make slides FILE=docs/presentation.md
FILE ?= docs/presentation.md
slides:
	@basename="$$(basename $(FILE) .md)"; \
	dir="$$(dirname $(FILE))"; \
	npx @marp-team/marp-cli $(FILE) --pdf --allow-local-files -o "$${dir}/$${basename}.pdf"; \
	echo "✅ Generated $${dir}/$${basename}.pdf"

# スライドをHTMLに変換
# 使用例: make slides-html FILE=docs/presentation.md
slides-html:
	@basename="$$(basename $(FILE) .md)"; \
	dir="$$(dirname $(FILE))"; \
	npx @marp-team/marp-cli $(FILE) --html --allow-local-files -o "$${dir}/$${basename}.html"; \
	echo "✅ Generated $${dir}/$${basename}.html"

# ヘルプ
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  up              - Start app and initialize data"
	@echo "  down            - Stop app"
	@echo "  start           - Start app (no data init)"
	@echo "  stop            - Stop app (keep containers)"
	@echo "  restart         - Restart all services"
	@echo "  restart-backend - Restart backend only"
	@echo "  restart-frontend - Rebuild frontend"
	@echo "  logs            - Show all logs"
	@echo "  logs-backend    - Show backend logs"
	@echo "  logs-frontend   - Show frontend logs"
	@echo "  init            - Initialize movie index"
	@echo "  reindex         - Recreate movie index"
	@echo "  clear-redis     - Clear Redis data"
	@echo "  reset-data      - Reset all data (ES + Redis)"
	@echo "  clean           - Stop and remove volumes"
	@echo "  rebuild         - Full rebuild with data init"
	@echo "  slides          - Generate PDF (FILE=docs/xxx.md)"
	@echo "  slides-html     - Generate HTML (FILE=docs/xxx.md)"
	@echo ""
	@echo "Examples:"
	@echo "  make slides                         # Default: docs/presentation.md"
	@echo "  make slides FILE=docs/other.md      # Specify file"
