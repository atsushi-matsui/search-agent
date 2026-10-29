import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.agents.answer import AnswerAgent
from app.agents.conversation_analyzer import ConversationAnalyzerAgent
from app.agents.preference_updater import PreferenceUpdaterAgent
from app.agents.query_to_es import QueryToESAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.agents.rerank import RerankAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.user_preference import UserPreferenceAgent
from app.core.redis import redis_client
from app.models.conversation import ConversationContext, ConversationTurn, PreferenceSnapshot
from app.models.search import AgentTiming, RankedMovie, SearchRequest, SearchResponse

logger = logging.getLogger("SearchOrchestrator")


class SearchOrchestrator:
    """検索エージェントのオーケストレーター"""

    def __init__(self, index_name: str = "movies"):
        self.conversation_analyzer_agent = ConversationAnalyzerAgent()
        self.query_understanding_agent = QueryUnderstandingAgent()
        self.user_preference_agent = UserPreferenceAgent()
        self.query_to_es_agent = QueryToESAgent(index_name)
        self.retrieval_agent = RetrievalAgent(index_name)
        self.rerank_agent = RerankAgent()
        self.answer_agent = AnswerAgent()
        self.preference_updater_agent = PreferenceUpdaterAgent()
        self._executor = ThreadPoolExecutor(max_workers=4)

    def search(self, request: SearchRequest) -> SearchResponse:
        total_start = time.perf_counter()
        user_id = request.user_id
        session_id = request.session_id
        skip_agents = set(request.skip_agents)

        logger.info("=" * 60)
        logger.info(f"[SEARCH START] query='{request.query}', user_id={user_id}, session_id={session_id}, skip={skip_agents}")
        logger.info("=" * 60)

        processing_steps = []
        agent_timings: list[AgentTiming] = []

        # 0. セッション取得/作成
        logger.info("-" * 40)
        logger.info("[PHASE 0/8] Session Management")
        logger.info("-" * 40)
        context = redis_client.get_conversation_context(session_id, user_id)
        if context is None:
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                turns=[],
                current_constraints=[],
                created_at=datetime.now().isoformat(),
            )
            processing_steps.append("Session: 新規セッション作成")
        else:
            processing_steps.append(f"Session: 既存セッション継続 (ターン数: {len(context.turns)})")

        # 現在の嗜好をスナップショットとして取得（ターン開始時点）
        current_preference_snapshot = None
        if user_id:
            current_pref = redis_client.get_user_preference(user_id)
            current_preference_snapshot = PreferenceSnapshot(preference=current_pref)

        # 1. Conversation Analyzer
        logger.info("-" * 40)
        logger.info("[PHASE 1/8] Conversation Analyzer Agent")
        logger.info("-" * 40)
        processing_steps.append("Conversation Analyzer Agent: 会話意図を分析中...")
        with self.conversation_analyzer_agent.measure_time():
            conversation_intent = self.conversation_analyzer_agent.execute(request.query, context)
        agent_timings.append(AgentTiming(
            agent_name="ConversationAnalyzer",
            duration_ms=self.conversation_analyzer_agent.get_last_duration_ms(),
            phase=1,
        ))

        action_summary = ", ".join([f"{a.type}:{a.constraints}" for a in conversation_intent.actions])
        search_behavior = conversation_intent.search_behavior

        # 検証用: リクエストで検索行動タイプが上書きされている場合
        if request.override_search_behavior:
            search_behavior = request.override_search_behavior
            logger.info(f"[SEARCH BEHAVIOR] overridden to: {search_behavior}")

        processing_steps.append(
            f"  → actions: [{action_summary}], "
            f"継続: {conversation_intent.is_continuation}, "
            f"behavior: {search_behavior}"
        )

        # goal_orientedの場合、LLMを使うエージェントをスキップ
        if search_behavior == "goal_oriented":
            skip_agents.update(["Rerank", "Answer"])
            logger.info(f"[SEARCH BEHAVIOR] goal_oriented → Rerank/Answerをスキップ")

        # actionsを順番に処理
        should_search = False
        refine_constraints: list[str] = []
        expand_constraints: list[str] = []
        applied_intent_type = "initial"

        for action in conversation_intent.actions:
            if action.type == "reset_all":
                self._apply_reset_all(context, user_id, processing_steps)
                context.current_constraints = []
            elif action.type == "undo":
                self._apply_undo(context, user_id, processing_steps)
            elif action.type == "initial":
                context.current_constraints = action.constraints.copy()
                refine_constraints = action.constraints.copy()
                applied_intent_type = "initial"
                should_search = True
            elif action.type == "refine":
                context.current_constraints = context.current_constraints + action.constraints
                refine_constraints = refine_constraints + action.constraints
                applied_intent_type = "refine"
                should_search = True
            elif action.type == "expand":
                context.current_constraints = context.current_constraints + action.constraints
                expand_constraints = expand_constraints + action.constraints
                applied_intent_type = "expand"
                should_search = True

        # 検索条件がない場合は早期リターン
        if not should_search:
            return self._build_no_search_response(request, context, processing_steps)

        # 2. Query Understanding
        logger.info("-" * 40)
        logger.info("[PHASE 2/8] Query Understanding Agent")
        logger.info("-" * 40)
        processing_steps.append("Query Understanding Agent: クエリを構造化中...")
        with self.query_understanding_agent.measure_time():
            structured_query = self.query_understanding_agent.execute(request.query)
        agent_timings.append(AgentTiming(
            agent_name="QueryUnderstanding",
            duration_ms=self.query_understanding_agent.get_last_duration_ms(),
            phase=2,
        ))
        processing_steps.append(
            f"  → 意図: {structured_query.intent}, "
            f"ジャンル: {structured_query.genres}, "
            f"雰囲気: {structured_query.mood_tags}"
        )

        # 3. User Preference (Redisから取得のみ)
        logger.info("-" * 40)
        logger.info("[PHASE 3/8] User Preference Agent")
        logger.info("-" * 40)
        processing_steps.append("User Preference Agent: ユーザー嗜好を取得中...")
        with self.user_preference_agent.measure_time():
            user_preference = self.user_preference_agent.execute(user_id)
        agent_timings.append(AgentTiming(
            agent_name="UserPreference",
            duration_ms=self.user_preference_agent.get_last_duration_ms(),
            phase=3,
        ))
        if user_preference:
            processing_steps.append(
                f"  → 好みジャンル: {user_preference.preferred_genres}, "
                f"ブースト条件: {len(user_preference.boost_conditions)}件"
            )
        else:
            processing_steps.append("  → 嗜好なし（新規ユーザー）")

        # 4. Query to ES (統合エージェント)
        logger.info("-" * 40)
        logger.info("[PHASE 4/8] Query to ES Agent")
        logger.info("-" * 40)
        processing_steps.append("Query to ES Agent: Elasticsearch DSLを生成中...")

        # 前回のDSLを取得（継続の場合）
        previous_dsl = None
        if context.turns and conversation_intent.is_continuation:
            last_turn = context.turns[-1]
            if last_turn.es_dsl:
                previous_dsl = last_turn.es_dsl
                processing_steps.append("  → 前回DSLを継続")

        if refine_constraints:
            processing_steps.append(f"  → refine制約 (AND): {refine_constraints}")
        if expand_constraints:
            processing_steps.append(f"  → expand制約 (OR): {expand_constraints}")

        with self.query_to_es_agent.measure_time():
            es_dsl = self.query_to_es_agent.execute(
                structured_query,
                user_preference,
                refine_constraints=refine_constraints,
                expand_constraints=expand_constraints,
                previous_dsl=previous_dsl,
                search_behavior=search_behavior,
            )
        agent_timings.append(AgentTiming(
            agent_name="QueryToES",
            duration_ms=self.query_to_es_agent.get_last_duration_ms(),
            phase=4,
        ))
        processing_steps.append(f"  → DSL: {json.dumps(es_dsl.query, ensure_ascii=False)}")

        # 5. Retrieval
        logger.info("-" * 40)
        logger.info("[PHASE 5/8] Retrieval Agent")
        logger.info("-" * 40)
        processing_steps.append("Retrieval Agent: Elasticsearchから検索中...")
        with self.retrieval_agent.measure_time():
            movies = self.retrieval_agent.execute(es_dsl)
        agent_timings.append(AgentTiming(
            agent_name="Retrieval",
            duration_ms=self.retrieval_agent.get_last_duration_ms(),
            phase=5,
        ))
        top10_info = [
            f"{m.id}: {m.title} (score={m.score:.2f})"
            for m in movies[:10]
        ]
        processing_steps.append(f"  → Top10: {top10_info}")

        # 6. Rerank
        logger.info("-" * 40)
        logger.info("[PHASE 6/8] Rerank Agent")
        logger.info("-" * 40)
        if "Rerank" in skip_agents:
            processing_steps.append("Rerank Agent: スキップ（ESスコア順を使用）")
            ranked_movies = [
                RankedMovie(
                    movie=m,
                    rank=i + 1,
                    relevance_score=m.score,
                    es_score=m.score,
                    llm_score=0.0,
                    explanation="Rerankスキップ",
                )
                for i, m in enumerate(movies)
            ]
            agent_timings.append(AgentTiming(agent_name="Rerank", duration_ms=0.0, phase=6))
        else:
            processing_steps.append("Rerank Agent: 結果を再ランキング中...")
            with self.rerank_agent.measure_time():
                ranked_movies = self.rerank_agent.execute(
                    movies, structured_query, user_preference
                )
            agent_timings.append(AgentTiming(
                agent_name="Rerank",
                duration_ms=self.rerank_agent.get_last_duration_ms(),
                phase=6,
            ))
            rerank_details = [
                f"{rm.movie.title}: ES={rm.es_score:.2f}, LLM={rm.llm_score:.2f} → Final={rm.relevance_score:.2f}"
                for rm in ranked_movies[:10]
            ]
            processing_steps.append(f"  → スコア内訳: {rerank_details}")

        # 7. Answer Generation
        logger.info("-" * 40)
        logger.info("[PHASE 7/8] Answer Agent")
        logger.info("-" * 40)
        if "Answer" in skip_agents:
            processing_steps.append("Answer Agent: スキップ")
            explanation = ""
            agent_timings.append(AgentTiming(agent_name="Answer", duration_ms=0.0, phase=7))
        else:
            processing_steps.append("Answer Agent: 回答を生成中...")
            with self.answer_agent.measure_time():
                explanation = self.answer_agent.execute(ranked_movies, structured_query)
            agent_timings.append(AgentTiming(
                agent_name="Answer",
                duration_ms=self.answer_agent.get_last_duration_ms(),
                phase=7,
            ))
            processing_steps.append("  → 回答生成完了")

        # 結果を指定件数に制限
        final_results = ranked_movies[: request.size]

        # 8. Preference Update & Query History (user_idがある場合のみ、非同期実行)
        query_history_id = None
        if user_id:
            logger.info("-" * 40)
            logger.info("[PHASE 8/8] Preference Updater Agent (非同期)")
            logger.info("-" * 40)

            # 検索クエリ履歴を保存（IDを取得）- これは同期で実行（undo用に必要）
            result_movie_ids = [rm.movie.id for rm in final_results]
            query_history_id = redis_client.add_query_history(user_id, request.query, result_movie_ids)

            if "PreferenceUpdater" in skip_agents:
                processing_steps.append("Preference Updater Agent: スキップ")
            else:
                # 非同期でバックグラウンド実行（レスポンスを待たない）
                self._executor.submit(
                    self._run_preference_updater_async,
                    user_id, structured_query, ranked_movies
                )
                processing_steps.append("Preference Updater Agent: バックグラウンドで実行中...")
        else:
            logger.info("-" * 40)
            logger.info("[PHASE 8/8] Skipped (no user_id)")
            logger.info("-" * 40)

        # 会話ターンを保存（スナップショット・DSL・履歴IDを含む）
        turn = ConversationTurn(
            query=request.query,
            intent_type=applied_intent_type,
            constraints=context.current_constraints.copy(),
            result_movie_ids=[rm.movie.id for rm in final_results],
            es_dsl=es_dsl.model_dump(),
            preference_snapshot=current_preference_snapshot,
            query_history_id=query_history_id,
            timestamp=datetime.now().isoformat(),
        )
        context.turns.append(turn)
        redis_client.save_conversation_context(session_id, context, user_id)

        total_duration_ms = (time.perf_counter() - total_start) * 1000

        logger.info("=" * 60)
        logger.info(f"[SEARCH COMPLETE] 結果: {len(final_results)}件, 適用制約: {context.current_constraints}, 合計時間: {total_duration_ms:.1f}ms")
        logger.info("=" * 60)

        return SearchResponse(
            query=request.query,
            session_id=session_id,
            results=final_results,
            explanation=explanation,
            applied_constraints=context.current_constraints,
            processing_steps=processing_steps,
            agent_timings=agent_timings,
            total_duration_ms=total_duration_ms,
        )

    def _run_preference_updater_async(
        self,
        user_id: str,
        structured_query,
        ranked_movies: list,
    ) -> None:
        """PreferenceUpdaterをバックグラウンドで実行"""
        try:
            logger.info("[ASYNC] PreferenceUpdater 開始")
            updated_preference = self.preference_updater_agent.execute(
                user_id, structured_query, ranked_movies
            )
            logger.info(
                f"[ASYNC] PreferenceUpdater 完了: genres={updated_preference.preferred_genres}, "
                f"boost_conditions={len(updated_preference.boost_conditions)}件"
            )
        except Exception as e:
            logger.error(f"[ASYNC] PreferenceUpdater エラー: {e}")

    def _apply_reset_all(
        self,
        context: ConversationContext,
        user_id: str | None,
        processing_steps: list[str],
    ) -> None:
        """reset_all: セッション履歴をクリアし、嗜好をセッション開始前に戻す"""
        processing_steps.append("Reset All: セッションを完全リセット中...")

        if user_id and context.turns:
            # セッション内で保存されたquery_history_idsを収集
            history_ids = [t.query_history_id for t in context.turns if t.query_history_id]
            if history_ids:
                redis_client.remove_query_history_by_ids(user_id, history_ids)
                processing_steps.append(f"  → 検索履歴を{len(history_ids)}件削除")

            # 最初のターンのスナップショット（セッション開始前の状態）に復元
            first_turn = context.turns[0]
            if first_turn.preference_snapshot:
                redis_client.restore_preference(user_id, first_turn.preference_snapshot.preference)
                processing_steps.append("  → 嗜好をセッション開始前の状態に復元")

        # セッションをクリア
        context.turns = []
        processing_steps.append("  → セッション履歴をクリア")

        logger.info("[RESET_ALL] セッションをリセットしました")

    def _apply_undo(
        self,
        context: ConversationContext,
        user_id: str | None,
        processing_steps: list[str],
    ) -> None:
        """undo: 直前のターンを取り消し、前々回の状態から継続"""
        processing_steps.append("Undo: 直前のターンを取り消し中...")

        if not context.turns:
            processing_steps.append("  → 取り消すターンがありません")
            return

        # 直前のターンを取得して削除
        last_turn = context.turns.pop()

        if user_id:
            # 直前のターンのquery_historyを削除
            if last_turn.query_history_id:
                redis_client.remove_query_history_by_ids(user_id, [last_turn.query_history_id])
                processing_steps.append("  → 直前の検索履歴を削除")

            # 直前のターンのスナップショット（そのターン開始時点）に復元
            if last_turn.preference_snapshot:
                redis_client.restore_preference(user_id, last_turn.preference_snapshot.preference)
                processing_steps.append("  → 嗜好を直前のターン開始時点に復元")

        # 制約を前々回の状態に戻す
        if context.turns:
            prev_turn = context.turns[-1]
            context.current_constraints = prev_turn.constraints.copy()
            processing_steps.append(f"  → 制約を前回の状態に復元: {context.current_constraints}")
        else:
            context.current_constraints = []
            processing_steps.append("  → 初期状態に戻りました")

        logger.info(f"[UNDO] 制約: {context.current_constraints}")

    def _build_no_search_response(
        self,
        request: SearchRequest,
        context: ConversationContext,
        processing_steps: list[str],
    ) -> SearchResponse:
        """検索条件がない場合のレスポンスを生成"""
        redis_client.save_conversation_context(request.session_id, context, request.user_id)

        if context.current_constraints:
            explanation = f"現在の条件: {', '.join(context.current_constraints)}"
        else:
            explanation = "条件がリセットされました。新しい検索をお試しください。"

        logger.info("=" * 60)
        logger.info(f"[NO SEARCH] 制約: {context.current_constraints}")
        logger.info("=" * 60)

        return SearchResponse(
            query=request.query,
            session_id=request.session_id,
            results=[],
            explanation=explanation,
            applied_constraints=context.current_constraints,
            processing_steps=processing_steps,
        )
