import json
import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


class BaseAgent(ABC):
    """エージェントの基底クラス"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._last_duration_ms: float = 0.0

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """エージェントの実行"""
        pass

    def get_last_duration_ms(self) -> float:
        """直前のexecute呼び出しの処理時間（ミリ秒）を取得"""
        return self._last_duration_ms

    @contextmanager
    def measure_time(self) -> Generator[None, None, None]:
        """処理時間を計測するコンテキストマネージャー"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._last_duration_ms = elapsed * 1000
            self.logger.info(f"[TIMING] {self._last_duration_ms:.1f}ms")

    def log_input(self, data: Any):
        """入力データをログ出力"""
        self.logger.info(f"[INPUT] {self._format_data(data)}")

    def log_output(self, data: Any):
        """出力データをログ出力"""
        self.logger.info(f"[OUTPUT] {self._format_data(data)}")

    def log_step(self, message: str):
        """処理ステップをログ出力"""
        self.logger.info(f"[STEP] {message}")

    def _format_data(self, data: Any) -> str:
        """データを整形して文字列化"""
        if hasattr(data, "model_dump"):
            return json.dumps(data.model_dump(), ensure_ascii=False, indent=2)
        elif isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return str(data)
