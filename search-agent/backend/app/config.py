from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ELASTICSEARCH_HOST: str = "http://localhost:9200"
    REDIS_HOST: str = "redis://localhost:6379"
    VERTEX_PROJECT_ID: str = "xxx"
    VERTEX_REGION: str = "us-east5"

    # LLMモデル設定（タスク複雑度に応じて使い分け）
    MODEL_OPUS: str = "claude-opus-4-5@20251101"
    MODEL_SONNET: str = "claude-sonnet-4@20250514"
    MODEL_HAIKU: str = "claude-haiku-4-5@20251001"

    # デフォルトモデル
    DEFAULT_MODEL_TIER: str = "opus"

    # エージェント別モデル設定（未設定のエージェントはDEFAULT_MODEL_TIERを使用）
    # 形式: "エージェント名:モデルティア" をカンマ区切り
    # 例: "QueryToESAgent:sonnet,RerankAgent:haiku"
    AGENT_MODEL_CONFIG: str = "QueryToESAgent:sonnet"

    # プロンプト別バージョン設定（未設定のプロンプトは最新バージョンを使用）
    # 形式: "プロンプト名:バージョン" をカンマ区切り（プロンプト名は app/prompts 配下のディレクトリ名）
    # 例: "rerank:v1,query_to_es:v2"
    PROMPT_VERSION_CONFIG: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
