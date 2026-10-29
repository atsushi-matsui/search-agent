import json
import logging
import uuid
from datetime import datetime

import redis

from app.config import settings
from app.models.conversation import ConversationContext
from app.models.user import UserPreferenceData, QueryHistory

logger = logging.getLogger("RedisClient")


SESSION_TTL_SECONDS = 1800  # 30分


class RedisClient:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_HOST, decode_responses=True)
        self._prefix_preference = "user:preference:"
        self._prefix_query_history = "user:query_history:"
        self._prefix_session = "session:context:"

    def get_user_preference(self, user_id: str) -> UserPreferenceData | None:
        """ユーザー嗜好を取得"""
        key = f"{self._prefix_preference}{user_id}"
        data = self.client.get(key)
        if data:
            logger.info(f"[REDIS] ユーザー嗜好を取得: user_id={user_id}")
            return UserPreferenceData(**json.loads(data))
        logger.info(f"[REDIS] ユーザー嗜好なし: user_id={user_id}")
        return None

    def save_user_preference(self, user_id: str, preference: UserPreferenceData) -> None:
        """ユーザー嗜好を保存"""
        key = f"{self._prefix_preference}{user_id}"
        preference.updated_at = datetime.now().isoformat()
        self.client.set(key, json.dumps(preference.model_dump(), ensure_ascii=False))
        logger.info(f"[REDIS] ユーザー嗜好を保存: user_id={user_id}")

    def get_query_history(self, user_id: str, limit: int = 20) -> list[QueryHistory]:
        """検索クエリ履歴を取得（新しい順）"""
        key = f"{self._prefix_query_history}{user_id}"
        data = self.client.lrange(key, 0, limit - 1)
        histories = [QueryHistory(**json.loads(item)) for item in data]
        logger.info(f"[REDIS] クエリ履歴を取得: user_id={user_id}, count={len(histories)}")
        return histories

    def add_query_history(self, user_id: str, query: str, result_movie_ids: list[str]) -> str:
        """検索クエリ履歴を追加し、生成されたIDを返す"""
        key = f"{self._prefix_query_history}{user_id}"
        history_id = str(uuid.uuid4())
        history = QueryHistory(
            id=history_id,
            query=query,
            result_movie_ids=result_movie_ids,
            timestamp=datetime.now().isoformat(),
        )
        self.client.lpush(key, json.dumps(history.model_dump(), ensure_ascii=False))
        self.client.ltrim(key, 0, 99)
        logger.info(f"[REDIS] クエリ履歴を追加: user_id={user_id}, id={history_id}, query='{query}'")
        return history_id

    def remove_query_history_by_ids(self, user_id: str, ids: list[str]) -> int:
        """指定したIDの検索履歴を削除"""
        if not ids:
            return 0

        key = f"{self._prefix_query_history}{user_id}"
        ids_set = set(ids)

        all_items = self.client.lrange(key, 0, -1)
        items_to_keep = []

        for item in all_items:
            history = json.loads(item)
            if history.get("id") not in ids_set:
                items_to_keep.append(item)

        removed_count = len(all_items) - len(items_to_keep)

        if removed_count > 0:
            self.client.delete(key)
            if items_to_keep:
                self.client.rpush(key, *items_to_keep)

        logger.info(f"[REDIS] クエリ履歴を削除: user_id={user_id}, removed={removed_count}")
        return removed_count

    def restore_preference(self, user_id: str, snapshot: UserPreferenceData | None) -> None:
        """嗜好データをスナップショットから復元"""
        if snapshot is None:
            self.client.delete(f"{self._prefix_preference}{user_id}")
            logger.info(f"[REDIS] 嗜好を削除（復元先がNone）: user_id={user_id}")
        else:
            self.save_user_preference(user_id, snapshot)
            logger.info(f"[REDIS] 嗜好を復元: user_id={user_id}")

    def delete_user_data(self, user_id: str) -> None:
        """ユーザーデータを削除"""
        self.client.delete(f"{self._prefix_preference}{user_id}")
        self.client.delete(f"{self._prefix_query_history}{user_id}")
        logger.info(f"[REDIS] ユーザーデータを削除: user_id={user_id}")

    def _get_session_key(self, user_id: str | None, session_id: str) -> str:
        """セッションキーを生成: session:context:{user_id}:{session_id}"""
        uid = user_id or "anonymous"
        return f"{self._prefix_session}{uid}:{session_id}"

    def get_conversation_context(
        self, session_id: str, user_id: str | None = None
    ) -> ConversationContext | None:
        """セッションの会話コンテキストを取得"""
        key = self._get_session_key(user_id, session_id)
        data = self.client.get(key)
        if data:
            logger.info(f"[REDIS] 会話コンテキストを取得: key={key}")
            return ConversationContext(**json.loads(data))
        logger.info(f"[REDIS] 会話コンテキストなし: key={key}")
        return None

    def save_conversation_context(
        self, session_id: str, context: ConversationContext, user_id: str | None = None
    ) -> None:
        """セッションの会話コンテキストを保存（TTL: 30分）"""
        key = self._get_session_key(user_id, session_id)
        context.updated_at = datetime.now().isoformat()
        self.client.setex(
            key,
            SESSION_TTL_SECONDS,
            json.dumps(context.model_dump(), ensure_ascii=False)
        )
        logger.info(f"[REDIS] 会話コンテキストを保存: key={key}, turns={len(context.turns)}")


redis_client = RedisClient()
