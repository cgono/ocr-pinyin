from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from app.adapters.pinyin_provider import RawPinyinSegment
from app.main import app
from app.schemas.diagnostics import CostEstimate
from app.services import budget_service
from app.services.pinyin_service import PinyinServiceError


class StubPinyinProvider:
    def __init__(self, mapping: dict[str, list[RawPinyinSegment]]) -> None:
        self._mapping = mapping

    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        return self._mapping[text]


class StubTranslationProvider:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def translate(self, *, text: str, target_language: str) -> str:
        _ = target_language
        return self._mapping[text]


client = TestClient(app)


def _reset_daily_costs() -> None:
    budget_service.daily_cost_store.__dict__.update(
        budget_service.DailyCostStore().__dict__
    )


@pytest.fixture(autouse=True)
def _clean_daily_cost_store() -> None:
    _reset_daily_costs()


def _set_today_spend_sgd(sgd: float) -> None:
    _reset_daily_costs()
    estimated_usd = round(sgd / budget_service._USD_TO_SGD, 8)
    budget_service.record_request_cost(
        CostEstimate(estimated_usd=estimated_usd, estimated_sgd=sgd, confidence="full")
    )


def test_process_text_route_returns_success_with_shared_result_shape(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")

    with patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            {
                "老师说 Hello": [
                    RawPinyinSegment(hanzi="老", pinyin="lǎo"),
                    RawPinyinSegment(hanzi="师", pinyin="shī"),
                    RawPinyinSegment(hanzi="说", pinyin="shuō"),
                    RawPinyinSegment(hanzi=" ", pinyin=" "),
                    RawPinyinSegment(hanzi="H", pinyin="H"),
                    RawPinyinSegment(hanzi="e", pinyin="e"),
                    RawPinyinSegment(hanzi="l", pinyin="l"),
                    RawPinyinSegment(hanzi="l", pinyin="l"),
                    RawPinyinSegment(hanzi="o", pinyin="o"),
                ],
                "同学们好": [
                    RawPinyinSegment(hanzi="同", pinyin="tóng"),
                    RawPinyinSegment(hanzi="学", pinyin="xué"),
                    RawPinyinSegment(hanzi="们", pinyin="men"),
                    RawPinyinSegment(hanzi="好", pinyin="hǎo"),
                ],
            }
        ),
    ), patch(
        "app.services.translation_service.get_translation_provider",
        return_value=StubTranslationProvider(
            {
                "老师说 Hello": "Teacher says hello",
                "同学们好": "Hello, students",
            }
        ),
    ):
        response = client.post(
            "/v1/process-text",
            json={"source_text": "老师说 Hello\n同学们好"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["pinyin"]["segments"][0]["source_text"] == "老师说 Hello"
    assert body["data"]["pinyin"]["segments"][0]["translation_text"] == "Teacher says hello"
    assert body["data"]["reading"]["provider"]["kind"] == "heuristic"
    assert body["diagnostics"]["upload_context"]["content_type"] == "text/plain"
    assert body["diagnostics"]["timing"]["ocr_ms"] == 0
    assert body["diagnostics"]["cost_estimate"]["confidence"] == "full"
    assert body["diagnostics"]["cost_estimate"]["estimated_usd"] > 0
    today = budget_service.datetime.date.today().isoformat()
    assert budget_service.daily_cost_store.snapshot()[today]["request_count"] == 1


def test_process_text_route_reports_unavailable_cost_when_translation_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    with patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            {
                "老师说 Hello": [
                    RawPinyinSegment(hanzi="老", pinyin="lǎo"),
                    RawPinyinSegment(hanzi="师", pinyin="shī"),
                    RawPinyinSegment(hanzi="说", pinyin="shuō"),
                    RawPinyinSegment(hanzi=" ", pinyin=" "),
                    RawPinyinSegment(hanzi="H", pinyin="H"),
                    RawPinyinSegment(hanzi="e", pinyin="e"),
                    RawPinyinSegment(hanzi="l", pinyin="l"),
                    RawPinyinSegment(hanzi="l", pinyin="l"),
                    RawPinyinSegment(hanzi="o", pinyin="o"),
                ],
            }
        ),
    ):
        response = client.post(
            "/v1/process-text",
            json={"source_text": "老师说 Hello"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["diagnostics"]["cost_estimate"]["confidence"] == "unavailable"
    assert budget_service.daily_cost_store.snapshot() == {}


def test_process_text_route_reports_unavailable_cost_when_translation_enrichment_fails(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")

    with patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            {
                "你好": [
                    RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                    RawPinyinSegment(hanzi="好", pinyin="hǎo"),
                ],
            }
        ),
    ), patch(
        "app.api.v1.process_text.enrich_translations",
        side_effect=RuntimeError("translation provider unavailable"),
    ):
        response = client.post("/v1/process-text", json={"source_text": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["diagnostics"]["cost_estimate"]["confidence"] == "unavailable"
    assert budget_service.daily_cost_store.snapshot() == {}


def test_process_text_route_rejects_empty_input() -> None:
    response = client.post("/v1/process-text", json={"source_text": "   "})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["category"] == "validation"
    assert body["error"]["code"] == "text_empty"


def test_process_text_route_rejects_non_chinese_input() -> None:
    response = client.post("/v1/process-text", json={"source_text": "Hello world"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["category"] == "validation"
    assert body["error"]["code"] == "text_no_chinese_text"


def test_process_text_route_rejects_oversized_input(monkeypatch) -> None:
    monkeypatch.setenv("TEXT_INPUT_MAX_CHARS", "5")
    response = client.post("/v1/process-text", json={"source_text": "你好世界这是"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["category"] == "validation"
    assert body["error"]["code"] == "text_too_long"


def test_process_text_route_returns_partial_on_pinyin_failure() -> None:
    with patch(
        "app.api.v1.process_text.generate_pinyin",
        side_effect=PinyinServiceError(
            code="pinyin_provider_unavailable",
            message="Pinyin generation is temporarily unavailable. Please try again.",
        ),
    ):
        response = client.post("/v1/process-text", json={"source_text": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["data"]["message"] is not None
    assert body["warnings"][0]["code"] == "pinyin_provider_unavailable"


def test_process_text_route_warns_when_daily_budget_threshold_is_reached(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(0.85)

    with patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            {
                "你好": [
                    RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                    RawPinyinSegment(hanzi="好", pinyin="hǎo"),
                ],
            }
        ),
    ), patch(
        "app.services.translation_service.get_translation_provider",
        return_value=StubTranslationProvider({"你好": "hello"}),
    ):
        response = client.post("/v1/process-text", json={"source_text": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["warnings"][0]["category"] == "budget"
    assert body["warnings"][0]["code"] == "budget_approaching_daily_limit"


def test_process_text_route_block_mode_with_exceeded_budget_returns_budget_error(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "block")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(1.0)

    with patch("app.services.pinyin_service.generate_pinyin") as generate_pinyin:
        response = client.post("/v1/process-text", json={"source_text": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["category"] == "budget"
    assert body["error"]["code"] == "budget_daily_limit_exceeded"
    generate_pinyin.assert_not_called()
