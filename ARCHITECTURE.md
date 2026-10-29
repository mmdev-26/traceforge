# TraceForge — design and limitations

## Trace model

A trace is a set of unique spans with finite start/end timestamps and optional parent IDs. Parent references, child containment and cycles are validated before analysis. Durations describe individual spans; run wall time is the interval from earliest start to latest end.

Exclusive time subtracts the **union** of immediate-child intervals, not their sum. Two parallel child calls therefore do not produce negative parent exclusive time. Costs and token usage are additive ownership values; do not repeat aggregate parent costs. Baseline comparisons report raw metric deltas rather than claiming statistical regressions.

This version inspects traces and compares recorded runs. It does not replay side-effecting tools, infer causality, provide OpenTelemetry ingestion or collect live sessions. Use explicit adapters for external trace formats.

## Included scenario

A plan call succeeds while two overlapping API calls include an upstream timeout. The parent has 60 ms exclusive time, 300 ms wall time and one reported error. A separate baseline shows a 100 ms wall-time increase.

## Next validation work

Trace-format adapters, critical-path semantics for explicit causal DAGs, redaction policies and safe mocked replay. None is claimed as implemented.

## Public-demo boundary

The hosted workbench is served over HTTPS behind nginx. User scenarios are processed on the server, not in the visitor browser. Input is capped at 512 KB, analysis runs in a separate process with a 3-second CPU limit, a 5-second wall deadline and a 256 MB address-space limit on Linux. At most two analysis workers run per service. The reverse proxy rate-limits analysis and disables request/response buffering to disk. The service runs as a dynamic unprivileged user with a read-only filesystem, private temporary directory and localhost-only network access. These are resource and isolation boundaries, not a claim of a completed security audit.

The UI adds a live evidence visualization and domain-specific quick controls. JSON remains available for full reproducibility. No submitted inputs are intentionally persisted. Public demos are for synthetic data only.
