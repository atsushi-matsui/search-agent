import json
import logging
from enum import Enum
from typing import Any

from anthropic import AnthropicVertex

from app.config import settings

logger = logging.getLogger("LLMClient")


class ModelTier(str, Enum):
    """モデルの性能レベル"""

    OPUS = "opus"  # 最高品質（複雑な推論）
    SONNET = "sonnet"  # バランス型（中程度の複雑さ）
    HAIKU = "haiku"  # 高速（単純タスク）


class LLMClient:
    def __init__(self):
        self.client = AnthropicVertex(
            project_id=settings.VERTEX_PROJECT_ID,
            region=settings.VERTEX_REGION,
        )
        self._model_map = {
            ModelTier.OPUS: settings.MODEL_OPUS,
            ModelTier.SONNET: settings.MODEL_SONNET,
            ModelTier.HAIKU: settings.MODEL_HAIKU,
        }
        self._default_tier = ModelTier(settings.DEFAULT_MODEL_TIER)
        self._agent_model_config = self._parse_agent_config()

    def _parse_agent_config(self) -> dict[str, ModelTier]:
        """エージェント別モデル設定をパース"""
        config: dict[str, ModelTier] = {}
        if not settings.AGENT_MODEL_CONFIG:
            return config
        for item in settings.AGENT_MODEL_CONFIG.split(","):
            item = item.strip()
            if ":" in item:
                agent_name, tier_str = item.split(":", 1)
                try:
                    config[agent_name.strip()] = ModelTier(tier_str.strip())
                except ValueError:
                    logger.warning(f"Invalid model tier '{tier_str}' for agent '{agent_name}'")
        return config

    def get_model_for_agent(self, agent_name: str) -> str:
        """エージェント名からモデル名を取得"""
        tier = self._agent_model_config.get(agent_name, self._default_tier)
        return self._model_map[tier]

    def _get_model(self, model_tier: ModelTier | None) -> str:
        """モデルティアからモデル名を取得"""
        if model_tier is None:
            return self._model_map[self._default_tier]
        return self._model_map.get(model_tier, self._model_map[self._default_tier])

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model_tier: ModelTier | None = None,
        agent_name: str | None = None,
    ) -> str:
        if agent_name:
            model = self.get_model_for_agent(agent_name)
        else:
            model = self._get_model(model_tier)
        message = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model_tier: ModelTier | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        response = self.generate(
            system_prompt, user_prompt, max_tokens, temperature, model_tier, agent_name
        )
        json_str = self._extract_json(response)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            logger.warning(f"Attempting to fix JSON with LLM...")
            return self._fix_json_with_llm(json_str, str(e))

    def _extract_json(self, response: str) -> str:
        """レスポンスからJSON部分を抽出"""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response

    def _fix_json_with_llm(self, broken_json: str, error_msg: str) -> dict[str, Any]:
        """LLMを使ってJSONの構文エラーを修正"""
        fix_prompt = f"""以下のJSONに構文エラーがあります。修正して正しいJSONのみを出力してください。

エラー: {error_msg}

JSON:
{broken_json}

修正後のJSONのみを出力:"""

        response = self.generate(
            "JSONの構文エラーを修正するアシスタント。正しいJSONのみを出力。",
            fix_prompt,
            max_tokens=4096,
            temperature=0.0,
            model_tier=ModelTier.HAIKU,
        )
        json_str = self._extract_json(response)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON fix failed: {e}")
            logger.error(f"Original JSON: {broken_json[:500]}")
            raise


llm_client = LLMClient()
