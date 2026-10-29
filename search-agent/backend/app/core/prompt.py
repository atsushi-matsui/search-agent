import logging
import re
from pathlib import Path
from string import Template

from app.config import settings

logger = logging.getLogger("PromptLoader")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_VERSION_FILE_PATTERN = re.compile(r"^v(\d+)\.md$")


class PromptLoader:
    """プロンプトファイルの読み込み

    プロンプトは prompts/{name}/v{N}.md に配置する。
    PROMPT_VERSION_CONFIG で指定がないプロンプトは最新バージョンを使用する。
    """

    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        self.prompts_dir = prompts_dir
        self._version_config = self._parse_version_config()
        self._cache: dict[tuple[str, str], str] = {}

    def _parse_version_config(self) -> dict[str, str]:
        """プロンプト別バージョン設定をパース"""
        config: dict[str, str] = {}
        if not settings.PROMPT_VERSION_CONFIG:
            return config
        for item in settings.PROMPT_VERSION_CONFIG.split(","):
            item = item.strip()
            if ":" in item:
                name, version = item.split(":", 1)
                config[name.strip()] = version.strip()
        return config

    def list_versions(self, name: str) -> list[str]:
        """利用可能なバージョンを古い順に取得"""
        prompt_dir = self.prompts_dir / name
        if not prompt_dir.is_dir():
            return []
        numbers = [
            int(m.group(1))
            for path in prompt_dir.iterdir()
            if (m := _VERSION_FILE_PATTERN.match(path.name))
        ]
        return [f"v{n}" for n in sorted(numbers)]

    def resolve_version(self, name: str) -> str:
        """使用するバージョンを決定（設定値 > 最新）"""
        versions = self.list_versions(name)
        if not versions:
            raise FileNotFoundError(f"Prompt not found: {self.prompts_dir / name}")

        version = self._version_config.get(name, versions[-1])
        if version not in versions:
            raise FileNotFoundError(
                f"Prompt version '{version}' not found for '{name}' (available: {versions})"
            )
        return version

    def load(self, name: str) -> str:
        """プロンプトを読み込む"""
        version = self.resolve_version(name)
        key = (name, version)
        if key not in self._cache:
            path = self.prompts_dir / name / f"{version}.md"
            self._cache[key] = path.read_text(encoding="utf-8").rstrip("\n")
            logger.info(f"[PROMPT] {name} を読み込み: version={version}")
        return self._cache[key]

    @staticmethod
    def render(template: str, **variables: str) -> str:
        """$name 形式のプレースホルダを置換（JSON例の { } はエスケープ不要）"""
        return Template(template).substitute(variables)


prompt_loader = PromptLoader()
