from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.models.conversation import (
    ConversationContext,
    ConversationIntent,
    IntentAction,
)


class ConversationAnalyzerAgent(BaseAgent):
    """会話の意図を分析するエージェント"""

    def __init__(self):
        super().__init__("ConversationAnalyzerAgent")
        self.system_prompt = prompt_loader.load("conversation_analyzer")

    def execute(
        self, query: str, context: ConversationContext | None
    ) -> ConversationIntent:
        self.log_step("会話意図の分析を開始")

        if context is None or len(context.turns) == 0:
            self.log_step("会話履歴なし - LLMでクエリ解析")
            user_prompt = f"""会話履歴: なし
制約: なし

発言: "{query}"
"""
            result = llm_client.generate_json(
                self.system_prompt, user_prompt, agent_name=self.name
            )
            actions = [
                IntentAction(
                    type=a.get("type", "initial"), constraints=a.get("constraints", [])
                )
                for a in result.get("actions", [{"type": "initial", "constraints": []}])
            ]
            search_behavior = result.get("search_behavior", "exploratory")
            self.log_step(f"意図判定完了: search_behavior={search_behavior}")
            return ConversationIntent(
                actions=actions,
                is_continuation=False,
                reasoning=result.get("reasoning", "新規検索"),
                search_behavior=search_behavior,
            )

        self.log_input(
            {
                "query": query,
                "previous_turns": len(context.turns),
                "current_constraints": context.current_constraints,
            }
        )

        history_summary = self._format_history(context)

        user_prompt = f"""会話履歴:
{history_summary}

制約: {context.current_constraints}

発言: "{query}"
"""

        self.log_step("LLMに意図分析をリクエスト")
        result = llm_client.generate_json(
            self.system_prompt, user_prompt, agent_name=self.name
        )

        actions = [
            IntentAction(
                type=a.get("type", "initial"), constraints=a.get("constraints", [])
            )
            for a in result.get("actions", [])
        ]
        search_behavior = result.get("search_behavior", "exploratory")

        intent = ConversationIntent(
            actions=actions,
            is_continuation=result.get("is_continuation", False),
            reasoning=result.get("reasoning", ""),
            search_behavior=search_behavior,
        )

        action_summary = ", ".join([f"{a.type}:{a.constraints}" for a in actions])
        self.log_step(
            f"意図判定完了: actions=[{action_summary}], continuation={intent.is_continuation}, behavior={search_behavior}"
        )
        self.log_output(intent)

        return intent

    def _format_history(self, context: ConversationContext) -> str:
        lines = []
        for i, turn in enumerate(context.turns[-5:], 1):
            lines.append(f'{i}. "{turn.query}"')
        return "\n".join(lines) if lines else "なし"
