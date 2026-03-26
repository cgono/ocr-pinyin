from app.core.metrics import MetricsStore


def test_metrics_store_snapshot_starts_at_zero() -> None:
    store = MetricsStore()

    assert store.snapshot() == {
        "process_requests_total": 0,
        "process_requests_success": 0,
        "process_requests_partial": 0,
        "process_requests_error": 0,
    }


def test_metrics_store_increment_tracks_outcomes() -> None:
    store = MetricsStore()

    store.increment("success")
    store.increment("partial")
    store.increment("error")

    assert store.snapshot() == {
        "process_requests_total": 3,
        "process_requests_success": 1,
        "process_requests_partial": 1,
        "process_requests_error": 1,
    }
