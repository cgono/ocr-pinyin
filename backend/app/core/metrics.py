from typing import Literal


class MetricsStore:
    def __init__(self) -> None:
        self.process_requests_total = 0
        self.process_requests_success = 0
        self.process_requests_partial = 0
        self.process_requests_error = 0

    def increment(self, outcome: Literal["success", "partial", "error"]) -> None:
        self.process_requests_total += 1

        if outcome == "success":
            self.process_requests_success += 1
        elif outcome == "partial":
            self.process_requests_partial += 1
        else:
            self.process_requests_error += 1

    def snapshot(self) -> dict[str, int]:
        return {
            "process_requests_total": self.process_requests_total,
            "process_requests_success": self.process_requests_success,
            "process_requests_partial": self.process_requests_partial,
            "process_requests_error": self.process_requests_error,
        }


metrics_store = MetricsStore()
