from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.models.query import StructuredQuery
from app.models.search import RankedMovie


class AnswerAgent(BaseAgent):
    """検索結果をユーザー向けに整形・説明するエージェント"""

    def __init__(self):
        super().__init__("AnswerAgent")
        self.system_prompt = prompt_loader.load("answer")

    def execute(
        self, ranked_movies: list[RankedMovie], structured_query: StructuredQuery
    ) -> str:
        self.log_step("回答生成を開始")
        self.log_input({
            "ranked_movies_count": len(ranked_movies),
            "original_query": structured_query.original_query,
            "intent": structured_query.intent,
        })

        if not ranked_movies:
            self.log_step("検索結果なし - デフォルトメッセージを返却")
            return "申し訳ありません、ご希望に合う作品が見つかりませんでした。別のキーワードでお試しください。"

        top_movies = ranked_movies[:5]
        self.log_step(f"上位{len(top_movies)}件を回答に使用")
        for rm in top_movies:
            self.logger.info(f"  - {rm.movie.title} (rank={rm.rank}, relevance={rm.relevance_score:.2f})")

        movies_info = self._format_movies(top_movies)

        user_prompt = f"""検索クエリ: "{structured_query.original_query}"
ユーザーの意図: {structured_query.intent}
雰囲気タグ: {structured_query.mood_tags}

推薦作品:
{movies_info}

上記の検索結果について、ユーザー向けの説明文を生成してください。"""

        self.log_step("LLMに回答生成をリクエスト")
        answer = llm_client.generate(
            self.system_prompt, user_prompt, max_tokens=500, temperature=0.3, agent_name=self.name
        )

        self.log_step("回答生成完了")
        self.logger.info(f"[ANSWER]\n{answer}")

        return answer

    def _format_movies(self, movies: list[RankedMovie]) -> str:
        lines = []
        for rm in movies:
            m = rm.movie
            genres = ", ".join(m.genres) if m.genres else "不明"
            lines.append(
                f"- {m.title} ({genres}) - 評価: {m.vote_average} - 理由: {rm.explanation}"
            )
        return "\n".join(lines)
