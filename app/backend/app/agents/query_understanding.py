from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.prompt import prompt_loader
from app.models.query import StructuredQuery


class QueryUnderstandingAgent(BaseAgent):
    """曖昧クエリを構造化するエージェント"""

    def __init__(self):
        super().__init__("QueryUnderstandingAgent")
        self.system_prompt = prompt_loader.load("query_understanding")

    def execute(self, query: str) -> StructuredQuery:
        self.log_step("曖昧クエリの構造化を開始")
        self.log_input({"query": query})

        user_prompt = f"Input: \"{query}\"\nOutput:"
        self.log_step("LLMにクエリ構造化をリクエスト")

        result = llm_client.generate_json(self.system_prompt, user_prompt, agent_name=self.name)
        result["original_query"] = query

        structured = StructuredQuery(**result)
        self.log_output(structured)
        self.log_step(f"構造化完了: intent='{structured.intent}', genres={structured.genres}, mood_tags={structured.mood_tags}")

        return structured
