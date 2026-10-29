import copy

from app.agents.base import BaseAgent
from app.core.elasticsearch import es_client
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.models.query import ElasticsearchDSL, StructuredQuery
from app.models.user import UserPreferenceData


class QueryToESAgent(BaseAgent):
    """StructuredQueryから直接Elasticsearch DSLを生成する統合エージェント"""

    def __init__(self, index_name: str = "movies"):
        super().__init__("QueryToESAgent")
        self.system_prompt = prompt_loader.load("query_to_es")
        self.index_name = index_name

    def execute(
        self,
        structured_query: StructuredQuery,
        user_preference: UserPreferenceData | None = None,
        refine_constraints: list[str] | None = None,
        expand_constraints: list[str] | None = None,
        previous_dsl: dict | None = None,
        search_behavior: str = "exploratory",
    ) -> ElasticsearchDSL:
        self.log_step("Query→ES DSL変換を開始")
        self.log_input({
            "genres": structured_query.genres,
            "mood_tags": structured_query.mood_tags,
            "keywords": structured_query.keywords,
            "has_user_preference": user_preference is not None,
            "refine_constraints": refine_constraints,
            "expand_constraints": expand_constraints,
            "has_previous_dsl": previous_dsl is not None,
            "search_behavior": search_behavior,
        })

        # goal_orientedの場合はLLMを使わずルールベースで全文検索
        if search_behavior == "goal_oriented":
            self.log_step("目的指向検索: ルールベースの全文検索DSLを生成")
            return self._generate_fulltext_dsl(structured_query)

        mapping_info = self._get_mapping_info()
        system_prompt = prompt_loader.render(self.system_prompt, mapping_info=mapping_info)

        user_prompt = f"""Input:
- genres: {structured_query.genres}
- mood_tags: {structured_query.mood_tags}
- keywords: {structured_query.keywords}

Output:"""

        self.log_step("LLMにDSL生成をリクエスト")
        result = llm_client.generate_json(system_prompt, user_prompt, agent_name=self.name)
        new_dsl = ElasticsearchDSL(**result)

        # 前回DSLがある場合、refine/expand制約をマージ
        if previous_dsl:
            has_refine = refine_constraints and len(refine_constraints) > 0
            has_expand = expand_constraints and len(expand_constraints) > 0

            if has_refine or has_expand:
                self.log_step(f"前回DSLとマージ: refine={has_refine}, expand={has_expand}")
                new_dsl = self._merge_dsl_with_constraints(
                    previous_dsl, new_dsl, refine_constraints or [], expand_constraints or []
                )
                self.log_step("DSLマージ完了")

        # ユーザー嗜好のブースト条件を適用（ヒット数は絞らない）
        if user_preference and user_preference.boost_conditions:
            new_dsl = self._apply_boost_conditions(new_dsl, user_preference)

        self.logger.info(f"[DSL QUERY]\n{self._format_data(new_dsl.query)}")
        return new_dsl

    def _apply_boost_conditions(
        self,
        dsl: ElasticsearchDSL,
        user_preference: UserPreferenceData,
    ) -> ElasticsearchDSL:
        """ユーザー嗜好のブースト条件をfunction_scoreで適用（マッチングには影響しない）"""
        base_query = copy.deepcopy(dsl.query)

        # function_scoreのfunctionsを構築
        functions = []

        # 通常のブースト条件（filter + weight）
        for boost_cond in user_preference.boost_conditions:
            if not boost_cond.values:
                continue

            if boost_cond.field == "genres":
                filter_clause = {"terms": {boost_cond.field: boost_cond.values}}
            else:
                filter_clause = {"match": {boost_cond.field: " ".join(boost_cond.values)}}

            functions.append({
                "filter": filter_clause,
                "weight": boost_cond.boost,
            })
            self.log_step(f"ブースト追加: {boost_cond.field}={boost_cond.values}, weight={boost_cond.boost}")

        if not functions:
            return dsl

        # function_scoreクエリでラップ（マッチングは元クエリのみ、スコアにブーストを乗算）
        function_score_query = {
            "function_score": {
                "query": base_query,
                "functions": functions,
                "score_mode": "sum",
                "boost_mode": "multiply",
            }
        }

        return ElasticsearchDSL(query=function_score_query, sort=dsl.sort, size=dsl.size)

    def _merge_dsl_with_constraints(
        self,
        previous_dsl: dict,
        new_dsl: ElasticsearchDSL,
        refine_constraints: list[str],
        expand_constraints: list[str],
    ) -> ElasticsearchDSL:
        """
        前回DSLと新規DSLをマージする

        - refine制約: AND条件として追加（filter句に追加）→ 結果を絞り込む
        - expand制約: OR条件として追加（should句に追加）→ 結果を拡張する
        """
        merged_query = copy.deepcopy(previous_dsl.get("query", {}))
        new_query = new_dsl.query

        # boolクエリでない場合はboolでラップ
        if "bool" not in merged_query:
            merged_query = {"bool": {"must": [merged_query]}}

        bool_query = merged_query["bool"]

        # 新規クエリの条件を抽出
        new_conditions = self._extract_conditions(new_query)

        # refine制約がある場合: filter句にAND条件として追加
        if refine_constraints:
            if "filter" not in bool_query:
                bool_query["filter"] = []
            elif not isinstance(bool_query["filter"], list):
                bool_query["filter"] = [bool_query["filter"]]

            # refine用の条件を抽出してfilterに追加
            refine_conditions = [c for c in new_conditions if self._is_condition_for_constraints(c, refine_constraints)]
            if refine_conditions:
                wrapped_condition = {
                    "bool": {
                        "should": refine_conditions,
                        "minimum_should_match": 1
                    }
                }
                bool_query["filter"].append(wrapped_condition)
                self.logger.info(f"[REFINE] Added {len(refine_conditions)} conditions to filter")
            elif new_conditions:
                # 条件マッチが見つからない場合は全条件をrefineとして扱う
                wrapped_condition = {
                    "bool": {
                        "should": new_conditions,
                        "minimum_should_match": 1
                    }
                }
                bool_query["filter"].append(wrapped_condition)
                self.logger.info(f"[REFINE] Added all {len(new_conditions)} conditions to filter (fallback)")

        # expand制約がある場合: should句にOR条件として追加
        if expand_constraints:
            if "should" not in bool_query:
                bool_query["should"] = []
            elif not isinstance(bool_query["should"], list):
                bool_query["should"] = [bool_query["should"]]

            # expand用の条件を抽出してshouldに追加
            expand_conditions = [c for c in new_conditions if self._is_condition_for_constraints(c, expand_constraints)]
            if expand_conditions:
                for condition in expand_conditions:
                    bool_query["should"].append(condition)
                self.logger.info(f"[EXPAND] Added {len(expand_conditions)} conditions to should")
            elif new_conditions and not refine_constraints:
                # 条件マッチが見つからず、refineもない場合は全条件をexpandとして扱う
                for condition in new_conditions:
                    bool_query["should"].append(condition)
                self.logger.info(f"[EXPAND] Added all {len(new_conditions)} conditions to should (fallback)")

            # minimum_should_match を設定（既存があれば維持）
            if "minimum_should_match" not in bool_query:
                bool_query["minimum_should_match"] = 1

        return ElasticsearchDSL(
            query=merged_query,
            sort=new_dsl.sort or previous_dsl.get("sort", [{"_score": {"order": "desc"}}]),
            size=new_dsl.size or previous_dsl.get("size", 20),
        )

    def _is_condition_for_constraints(self, condition: dict, constraints: list[str]) -> bool:
        """条件が特定の制約に対応するかチェック（簡易マッチング）"""
        condition_str = str(condition).lower()
        for constraint in constraints:
            # 制約のキーワードが条件に含まれていればマッチ
            keywords = constraint.lower().replace(":", " ").split()
            if any(keyword in condition_str for keyword in keywords):
                return True
        return False

    def _extract_conditions(self, query: dict) -> list[dict]:
        """クエリから条件を抽出"""
        conditions = []

        if "bool" in query:
            bool_query = query["bool"]
            # should, must, filter から条件を収集
            for clause_type in ["should", "must", "filter"]:
                if clause_type in bool_query:
                    clause = bool_query[clause_type]
                    if isinstance(clause, list):
                        conditions.extend(clause)
                    else:
                        conditions.append(clause)
        else:
            # boolでない場合はそのまま条件として追加
            conditions.append(query)

        return conditions

    def _get_mapping_info(self) -> str:
        try:
            mapping = es_client.get_mapping(self.index_name)
            properties = mapping[self.index_name]["mappings"].get("properties", {})
            fields = [f"- {name}: {config.get('type', 'unknown')}" for name, config in properties.items()]
            return "\n".join(fields)
        except Exception:
            return "- genres: keyword\n- overview: text\n- title: text"

    def _generate_fulltext_dsl(self, structured_query: StructuredQuery) -> ElasticsearchDSL:
        """ルールベースの全文検索DSL生成（LLMなし）"""
        # english_queryがあればそれを使用、なければoriginal_queryを使用
        query_text = structured_query.english_query or structured_query.original_query
        dsl = ElasticsearchDSL(
            query={
                "multi_match": {
                    "query": query_text,
                    "fields": ["*"],
                    "type": "best_fields",
                }
            },
            sort=[{"_score": {"order": "desc"}}, {"popularity": {"order": "desc"}}],
            size=20,
        )
        self.logger.info(f"[DSL QUERY (fulltext)] query='{query_text}'\n{self._format_data(dsl.query)}")
        return dsl
