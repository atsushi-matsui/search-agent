from pydantic import BaseModel, Field

from app.models.user import UserPreferenceData


class PreferenceSnapshot(BaseModel):
    """ターン開始時の嗜好スナップショット（ロールバック用）"""

    preference: UserPreferenceData | None = Field(
        default=None,
        description="このターン開始時点でのユーザー嗜好。Noneは嗜好なし（新規ユーザー等）"
    )


class ConversationTurn(BaseModel):
    """会話の1ターン"""

    query: str = Field(description="ユーザーの発言")
    intent_type: str = Field(description="意図タイプ: initial, refine, expand, reset_all, undo")
    constraints: list[str] = Field(default_factory=list, description="この時点での累積制約")
    result_movie_ids: list[str] = Field(default_factory=list, description="この検索で返した映画ID")
    es_dsl: dict | None = Field(default=None, description="このターンで使用したElasticsearch DSL")
    preference_snapshot: PreferenceSnapshot | None = Field(
        default=None, description="このターン開始時の嗜好スナップショット"
    )
    query_history_id: str | None = Field(default=None, description="query_historyのID（削除用）")
    timestamp: str = ""


class ConversationContext(BaseModel):
    """セッション内の会話コンテキスト"""

    session_id: str
    user_id: str | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    current_constraints: list[str] = Field(default_factory=list, description="現在有効な累積制約")
    created_at: str = ""
    updated_at: str = ""


class IntentAction(BaseModel):
    """単一の意図アクション"""

    type: str = Field(description="initial, refine, expand, undo, reset_all")
    constraints: list[str] = Field(default_factory=list, description="この操作で追加する制約")


class ConversationIntent(BaseModel):
    """会話意図の分析結果（複数アクション対応）"""

    actions: list[IntentAction] = Field(description="順番に適用されるアクションのリスト")
    is_continuation: bool = Field(default=False, description="前回の検索を継続するか")
    reasoning: str = Field(default="", description="判定理由")
    search_behavior: str = Field(
        default="exploratory",
        description="検索行動タイプ: exploratory, goal_oriented, comparative"
    )
