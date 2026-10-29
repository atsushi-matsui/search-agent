from pydantic import BaseModel, Field


class StructuredQuery(BaseModel):
    """Query Understanding Agentが出力する構造化クエリ"""

    original_query: str = Field(description="元のユーザークエリ")
    english_query: str = Field(default="", description="英語に翻訳したクエリ（全文検索用）")
    intent: str = Field(description="推定されたユーザーの意図")
    genres: list[str] = Field(default_factory=list, description="抽出されたジャンル")
    mood_tags: list[str] = Field(
        default_factory=list, description="雰囲気・感情タグ（例: ワクワク、ほっこり）"
    )
    keywords: list[str] = Field(
        default_factory=list, description="重要なキーワード"
    )
    time_period: str | None = Field(default=None, description="時代設定や年代")
    target_audience: str | None = Field(default=None, description="ターゲット層")


class ElasticsearchDSL(BaseModel):
    """QueryToESAgentが出力するElasticsearch DSL"""

    query: dict = Field(description="Elasticsearch クエリ DSL")
    sort: list[dict] | None = Field(default=None, description="ソート条件")
    size: int = Field(default=20, description="取得件数")
