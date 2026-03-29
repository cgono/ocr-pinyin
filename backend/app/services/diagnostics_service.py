from app.schemas.diagnostics import (
    CostEstimate,
    DiagnosticsPayload,
    TimingInfo,
    TraceInfo,
    UploadContext,
)


def build_diagnostics(
    *,
    upload_context: UploadContext,
    timing: TimingInfo,
    trace: TraceInfo,
    cost_estimate: CostEstimate | None = None,
) -> DiagnosticsPayload:
    return DiagnosticsPayload(
        upload_context=upload_context,
        timing=timing,
        trace=trace,
        cost_estimate=cost_estimate,
    )
