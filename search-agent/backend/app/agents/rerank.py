from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.models.query import StructuredQuery
from app.models.search import Movie, RankedMovie
from app.models.user import UserPreferenceData

ES_WEIGHT = 0.3
MAX_RERANK_MOVIES = 10  # LLMでリランクする最大映画数


class RerankAgent(BaseAgent):
    """検索結果を再ランキングするエージェント"""

    def __init__(self):
        super().__init__("RerankAgent")
        self.system_prompt = prompt_loader.load("rerank")

    def execute(
        self,
        movies: list[Movie],
        structured_query: StructuredQuery,
        user_preference: UserPreferenceData | None,
    ) -> list[RankedMovie]:
        self.log_step("検索結果の再ランキングを開始")
        preferred_genres = user_preference.preferred_genres if user_preference else []
        self.log_input({
            "movies_count": len(movies),
            "intent": structured_query.intent,
            "mood_tags": structured_query.mood_tags,
            "user_preferred_genres": preferred_genres,
        })

        if not movies:
            self.log_step("映画リストが空 - 空リストを返却")
            return []

        # LLMでリランクする映画数を制限
        movies_for_llm = movies[:MAX_RERANK_MOVIES]

        self.log_step(f"再ランキング対象: {len(movies_for_llm)}件 (全{len(movies)}件中)")
        for i, m in enumerate(movies_for_llm[:5], 1):
            self.logger.info(f"  入力{i}. {m.title} (genres={m.genres}, score={m.score:.2f})")

        movies_info = self._format_movies(movies_for_llm)
        user_prompt = f"""Intent: "{structured_query.intent}"
Mood: {structured_query.mood_tags}
Pref: {preferred_genres}
Movies:
{movies_info}"""

        self.log_step("LLMに再ランキングをリクエスト")
        result = llm_client.generate_json(self.system_prompt, user_prompt, agent_name=self.name)

        movie_map = {m.id: m for m in movies_for_llm}
        es_score_map = {m.id: m.score for m in movies_for_llm}

        rankings = result.get("rankings", [])
        if not rankings:
            return []

        llm_scores = [r["relevance_score"] for r in rankings]
        normalized_llm = self._normalize_scores(llm_scores)

        movie_ids = list(es_score_map.keys())
        es_scores = list(es_score_map.values())
        normalized_es = self._normalize_scores(es_scores)
        normalized_es_map = dict(zip(movie_ids, normalized_es))

        self.log_step(f"スコア統合: ES_WEIGHT={ES_WEIGHT}")

        ranked_movies = []
        for i, ranking in enumerate(rankings):
            movie_id = str(ranking["movie_id"])
            if movie_id in movie_map:
                normalized_es_score = normalized_es_map.get(movie_id, 0.0)
                normalized_llm_score = normalized_llm[i]
                final_score = ES_WEIGHT * normalized_es_score + (1 - ES_WEIGHT) * normalized_llm_score

                movie = movie_map[movie_id]
                self.logger.info(
                    f"  {movie.title}: ES={normalized_es_score:.3f}, LLM={normalized_llm_score:.3f} -> Final={final_score:.3f}"
                )

                ranked_movies.append(
                    RankedMovie(
                        movie=movie,
                        rank=ranking["rank"],
                        relevance_score=final_score,
                        es_score=normalized_es_score,
                        llm_score=normalized_llm_score,
                        explanation=ranking.get("explanation", ""),
                    )
                )

        ranked_movies.sort(key=lambda x: -x.relevance_score)

        self.log_step(f"再ランキング完了: {len(ranked_movies)}件")
        for rm in ranked_movies[:5]:
            self.logger.info(
                f"  順位{rm.rank}. {rm.movie.title} (relevance={rm.relevance_score:.2f}) - {rm.explanation[:50]}..."
            )

        return ranked_movies

    def _format_movies(self, movies: list[Movie]) -> str:
        lines = []
        for i, m in enumerate(movies, 1):
            genres = ",".join(m.genres[:2]) if m.genres else "?"
            lines.append(f"{i}.{m.title}(ID:{m.id},{genres})")
        return " ".join(lines)

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        if not scores:
            return []
        min_s, max_s = min(scores), max(scores)
        if max_s == min_s:
            return [1.0] * len(scores)
        return [(s - min_s) / (max_s - min_s) for s in scores]
