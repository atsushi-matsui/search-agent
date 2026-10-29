from pydantic import BaseModel, Field


class WatchHistory(BaseModel):
    """視聴履歴"""

    movie_id: str
    title: str
    genres: list[str] = Field(default_factory=list)
    watched_at: str = ""
    rating: float | None = None


class UserProfile(BaseModel):
    """ユーザープロファイル"""

    user_id: str
    watch_history: list[WatchHistory] = Field(default_factory=list)
    favorite_genres: list[str] = Field(default_factory=list)


class QueryHistory(BaseModel):
    """検索クエリ履歴"""

    id: str = Field(default="", description="履歴のID（削除用）")
    query: str
    result_movie_ids: list[str] = Field(default_factory=list)
    timestamp: str = ""


class BoostCondition(BaseModel):
    """QueryToESAgentで使用するブースト条件"""

    field: str = Field(description="ブースト対象のフィールド名")
    values: list[str] = Field(default_factory=list, description="マッチさせる値のリスト")
    boost: float = Field(default=1.0, description="ブースト値")


class UserPreferenceData(BaseModel):
    """Redisに保存するユーザー嗜好データ"""

    user_id: str
    preferred_genres: list[str] = Field(default_factory=list)
    genre_weights: dict[str, float] = Field(default_factory=dict)
    mood_preferences: list[str] = Field(default_factory=list)
    recent_search_themes: list[str] = Field(default_factory=list)
    boost_conditions: list[BoostCondition] = Field(
        default_factory=list, description="QueryToESで適用するブースト条件"
    )
    created_at: str = ""
    updated_at: str = ""
