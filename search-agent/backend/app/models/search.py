from pydantic import BaseModel, Field


class AgentTiming(BaseModel):
    """エージェントの処理時間"""

    agent_name: str = Field(description="エージェント名")
    duration_ms: float = Field(description="処理時間（ミリ秒）")
    phase: int = Field(description="フェーズ番号")


class Movie(BaseModel):
    """映画データ"""

    id: str
    title: str
    original_title: str = ""
    overview: str = ""
    genres: list[str] = Field(default_factory=list)
    popularity: float = 0.0
    vote_average: float = 0.0
    release_date: str = ""
    homepage: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    score: float = Field(default=0.0, description="検索スコア")


class RankedMovie(BaseModel):
    """Rerank後の映画データ"""

    movie: Movie
    rank: int = Field(description="最終順位")
    relevance_score: float = Field(description="関連性スコア（最終スコア）")
    es_score: float = Field(default=0.0, description="Elasticsearchスコア（正規化済み）")
    llm_score: float = Field(default=0.0, description="LLMスコア（正規化済み）")
    explanation: str = Field(default="", description="順位の説明")


class SearchRequest(BaseModel):
    """検索リクエスト"""

    query: str = Field(description="検索クエリ")
    user_id: str | None = Field(default=None, description="ユーザーID（嗜好取得用）")
    session_id: str = Field(description="セッションID（会話継続用、フロントエンドで生成）")
    size: int = Field(default=10, description="取得件数")
    skip_agents: list[str] = Field(default_factory=list, description="スキップするエージェント名のリスト")
    override_search_behavior: str | None = Field(
        default=None,
        description="検索行動タイプを上書き（検証用）: exploratory, goal_oriented, comparative"
    )


class SearchResponse(BaseModel):
    """検索レスポンス"""

    query: str = Field(description="元のクエリ")
    session_id: str = Field(default="", description="セッションID（会話継続用）")
    results: list[RankedMovie] = Field(description="検索結果")
    explanation: str = Field(default="", description="検索結果の説明")
    applied_constraints: list[str] = Field(default_factory=list, description="適用中の制約一覧")
    processing_steps: list[str] = Field(
        default_factory=list, description="処理ステップのログ"
    )
    agent_timings: list[AgentTiming] = Field(
        default_factory=list, description="各エージェントの処理時間"
    )
    total_duration_ms: float = Field(default=0.0, description="合計処理時間（ミリ秒）")
