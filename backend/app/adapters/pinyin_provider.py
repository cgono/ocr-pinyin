from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RawPinyinSegment:
    hanzi: str
    pinyin: str


class PinyinProvider(Protocol):
    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        """Convert Chinese text into per-character hanzi/pinyin pairs."""


class PinyinProviderUnavailableError(Exception):
    pass


class PinyinExecutionError(Exception):
    pass


class NoOpPinyinProvider:
    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        _ = text
        raise PinyinProviderUnavailableError("Pinyin provider is not configured")


def get_pinyin_provider() -> PinyinProvider:
    """Return the active pinyin provider.

    Supported values for PINYIN_PROVIDER env var:
      pypinyin  – local pypinyin library (default)
      (anything else) – NoOpPinyinProvider
    """
    import os

    provider = os.environ.get("PINYIN_PROVIDER", "pypinyin").lower()
    if provider == "pypinyin":
        from app.adapters.pypinyin_provider import PyPinyinProvider

        return PyPinyinProvider()
    return NoOpPinyinProvider()
