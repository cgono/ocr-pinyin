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
