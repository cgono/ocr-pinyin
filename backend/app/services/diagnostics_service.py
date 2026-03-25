from app.schemas.diagnostics import DiagnosticsPayload, TimingInfo, TraceInfo, UploadContext


def build_diagnostics(
    *,
    upload_context: UploadContext,
    timing: TimingInfo,
    trace: TraceInfo,
) -> DiagnosticsPayload:
    return DiagnosticsPayload(
        upload_context=upload_context,
        timing=timing,
        trace=trace,
    )
