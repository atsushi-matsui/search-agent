from datetime import datetime

from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.core.redis import redis_client
from app.models.query import StructuredQuery
from app.models.search import RankedMovie
from app.models.user import BoostCondition, UserPreferenceData


class PreferenceUpdaterAgent(BaseAgent):
    """検索結果に基づいてユーザー嗜好を更新するエージェント"""

    def __init__(self):
        super().__init__("PreferenceUpdaterAgent")
        self.system_prompt = prompt_loader.load("preference_updater")

    def execute(
        self,
        user_id: str,
        structured_query: StructuredQuery,
        ranked_movies: list[RankedMovie],
    ) -> UserPreferenceData:
        self.log_step("ユーザー嗜好の更新を開始")
        self.log_input({
            "user_id": user_id,
            "query": structured_query.original_query,
            "result_count": len(ranked_movies),
        })

        # 現在の嗜好を取得
        current_preference = redis_client.get_user_preference(user_id)

        # 過去の検索履歴を取得
        query_history = redis_client.get_query_history(user_id, limit=10)

        # 上位の検索結果からジャンルを抽出
        top_movies = ranked_movies[:5]
        result_genres = self._extract_genres(top_movies)
        self.log_step(f"検索結果のジャンル: {result_genres}")

        # LLMに渡すプロンプトを構築
        system_prompt = self.system_prompt
        current_summary = self._format_current_preference(current_preference)
        history_summary = self._format_query_history(query_history)
        result_summary = self._format_search_result(structured_query, top_movies, result_genres)

        user_prompt = f"""## 現在のユーザー嗜好
{current_summary}

## 過去の検索履歴（最新10件）
{history_summary}

## 今回の検索
{result_summary}

上記の情報を総合的に分析し、更新された嗜好情報をJSON形式で出力してください:"""

        self.log_step("LLMに嗜好更新をリクエスト")
        result = llm_client.generate_json(system_prompt, user_prompt, agent_name=self.name)

        # boost_conditionsをパース
        boost_conditions = []
        for bc in result.get("boost_conditions", []):
            boost_conditions.append(BoostCondition(
                field=bc.get("field", "genres"),
                values=bc.get("values", []),
                boost=bc.get("boost", 1.5),
            ))

        updated_preference = UserPreferenceData(
            user_id=user_id,
            preferred_genres=result.get("preferred_genres", []),
            genre_weights=result.get("genre_weights", {}),
            mood_preferences=result.get("mood_preferences", []),
            recent_search_themes=result.get("recent_search_themes", []),
            boost_conditions=boost_conditions,
            created_at=current_preference.created_at if current_preference else datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        # 嗜好を保存
        redis_client.save_user_preference(user_id, updated_preference)

        self.log_step(
            f"嗜好更新完了: genres={updated_preference.preferred_genres}, "
            f"boost_conditions={len(boost_conditions)}件"
        )
        self.log_output(updated_preference)

        return updated_preference

    def _extract_genres(self, movies: list[RankedMovie]) -> list[str]:
        """検索結果からジャンルを抽出"""
        genres = []
        for rm in movies:
            genres.extend(rm.movie.genres)
        genre_count = {}
        for g in genres:
            genre_count[g] = genre_count.get(g, 0) + 1
        sorted_genres = sorted(genre_count.keys(), key=lambda x: genre_count[x], reverse=True)
        return sorted_genres[:5]

    def _format_current_preference(self, preference: UserPreferenceData | None) -> str:
        if preference is None:
            return "- なし（新規ユーザー）"

        lines = [
            f"- 好みジャンル: {preference.preferred_genres}",
            f"- ジャンル重み: {preference.genre_weights}",
            f"- 雰囲気嗜好: {preference.mood_preferences}",
            f"- 最近の検索テーマ: {preference.recent_search_themes}",
        ]

        if preference.boost_conditions:
            boost_summary = [
                f"{bc.field}:{bc.values}(boost={bc.boost})"
                for bc in preference.boost_conditions
            ]
            lines.append(f"- 現在のブースト条件: {boost_summary}")

        return "\n".join(lines)

    def _format_query_history(self, history: list) -> str:
        if not history:
            return "- 履歴なし"

        lines = []
        for h in history[:10]:
            lines.append(f"- \"{h.query}\" ({h.timestamp[:10] if h.timestamp else '日付不明'})")
        return "\n".join(lines)

    def _format_search_result(
        self,
        structured_query: StructuredQuery,
        movies: list[RankedMovie],
        result_genres: list[str],
    ) -> str:
        movie_titles = [rm.movie.title for rm in movies]
        return f"""- 検索クエリ: "{structured_query.original_query}"
- 検索意図: {structured_query.intent}
- 抽出されたジャンル: {structured_query.genres}
- 雰囲気タグ: {structured_query.mood_tags}
- 結果上位映画: {movie_titles}
- 結果に含まれるジャンル: {result_genres}"""

