from app.agents.base import BaseAgent
from app.core.redis import redis_client
from app.models.user import UserPreferenceData


class UserPreferenceAgent(BaseAgent):
    """Redisからユーザー嗜好を取得するエージェント（LLM呼び出しなし）"""

    def __init__(self):
        super().__init__("UserPreferenceAgent")

    def execute(self, user_id: str | None) -> UserPreferenceData | None:
        """
        Redisからユーザー嗜好データを取得する。
        他の処理は行わず、取得のみを担当する。
        """
        self.log_step("ユーザー嗜好の取得を開始")
        self.log_input({"user_id": user_id})

        if user_id is None:
            self.log_step("user_idなし - 嗜好なしを返却")
            return None

        preference_data = redis_client.get_user_preference(user_id)

        if preference_data is None:
            self.log_step("Redis嗜好データなし")
            return None

        self.log_step(
            f"嗜好取得完了: preferred_genres={preference_data.preferred_genres}, "
            f"boost_conditions={len(preference_data.boost_conditions)}件"
        )
        self.log_output(preference_data)

        return preference_data
