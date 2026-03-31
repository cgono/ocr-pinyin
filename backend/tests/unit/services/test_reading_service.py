from app.schemas.process import PinyinData, PinyinSegment
from app.services.reading_service import build_reading_projection


def _make_segment(
    source_text: str,
    *,
    line_id: int | None,
    translation_text: str | None = None,
) -> PinyinSegment:
    return PinyinSegment(
        source_text=source_text,
        pinyin_text="placeholder",
        alignment_status="aligned",
        line_id=line_id,
        translation_text=translation_text,
    )


def test_build_reading_projection_groups_adjacent_segments_by_line_and_preserves_indexes() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("老师", line_id=0, translation_text="teacher"),
                _make_segment("好", line_id=0, translation_text="teacher"),
                _make_segment(
                    "我们开始上课",
                    line_id=1,
                    translation_text="we begin class",
                ),
            ]
        )
    )

    assert result is not None
    assert result.provider.kind == "heuristic"
    assert result.provider.applied is True
    assert result.groups[0].line_id == 0
    assert result.groups[0].segment_indexes == [0, 1]
    assert result.groups[0].raw_text == "老师好"
    assert result.groups[0].display_text == "老师好。"
    assert result.groups[1].segment_indexes == [2]
    assert result.groups[1].display_text == "我们开始上课。"


def test_build_reading_projection_never_crosses_line_boundaries() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("老师", line_id=0),
                _make_segment("同学们", line_id=1),
            ]
        )
    )

    assert result is not None
    assert [group.segment_indexes for group in result.groups] == [[0], [1]]
    assert [group.line_id for group in result.groups] == [0, 1]


def test_build_reading_projection_returns_none_when_no_safe_improvement_exists() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("老师。", line_id=0),
                _make_segment("同学们好！", line_id=1),
                _make_segment("旁白", line_id=None),
            ]
        )
    )

    assert result is None


def test_build_reading_projection_inserts_comma_after_mid_line_particle() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("太阳公公起床了公鸡", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.provider.version == "v2"
    assert result.groups[0].display_text == "太阳公公起床了，公鸡。"


def test_build_reading_projection_skips_comma_for_terminal_particle() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("你好了", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.groups[0].display_text == "你好了。"


def test_build_reading_projection_skips_comma_when_particle_is_too_close_to_clause_start() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("了解后续", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.groups[0].display_text == "了解后续。"


def test_build_reading_projection_skips_comma_when_particle_has_only_one_preceding_char() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("不了解", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.groups[0].display_text == "不了解。"


def test_build_reading_projection_inserts_multiple_particle_commas() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("起床了吃饭吧出门啊", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.groups[0].display_text == "起床了，吃饭吧，出门啊。"


def test_build_reading_projection_with_existing_terminal_punctuation_still_returns_none() -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("起床了。", line_id=0),
                _make_segment("吃饭吧！", line_id=1),
            ]
        )
    )

    assert result is None


def test_build_reading_projection_still_appends_terminal_punctuation_when_no_particles_exist(
) -> None:
    result = build_reading_projection(
        PinyinData(
            segments=[
                _make_segment("今天我们上课", line_id=0),
            ]
        )
    )

    assert result is not None
    assert result.groups[0].display_text == "今天我们上课。"
