import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, getToken } from "../api/client";

type Scan = {
  id: string;
  client_id: string;
  label: string | null;
  status: string;
  progress_pct: number;
  error_message: string | null;
  previous_scan_id: string | null;
  created_at: string;
  findings_count?: number;
};

type Finding = {
  id: string;
  fingerprint: string;
  severity: string;
  status: string;
  triage: string | null;
  description: string | null;
  resource_id: string;
  region: string;
  service: string;
  check_id: string;
  compliance_framework: string | null;
  remediation: string | null;
  remediation_url: string | null;
  created_at: string;
};

type PaginatedFindings = {
  total: number;
  items: Finding[];
};

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-900/60 text-red-300 border-red-700/50",
  high: "bg-orange-900/50 text-orange-300 border-orange-700/50",
  medium: "bg-yellow-900/40 text-yellow-300 border-yellow-700/40",
  low: "bg-sky-900/40 text-sky-300 border-sky-700/40",
};

const PAGE_SIZE = 50;

type DiffItem = {
  fingerprint: string;
  category: string;
  finding_id: string | null;
  severity: string | null;
  service: string | null;
  resource_id: string | null;
  description: string | null;
  check_id: string | null;
  remediation: string | null;
  remediation_url: string | null;
  triage: string | null;
};

type DiffOut = {
  scan_id: string;
  previous_scan_id: string | null;
  counts: Record<string, number>;
  items: DiffItem[];
};

type ResourceInstance = {
  id: string;
  resource_id: string;
  region: string;
  status: string;
  triage: string | null;
  fingerprint: string;
};

type GroupedFinding = {
  check_id: string;
  description: string | null;
  severity: string;
  service: string;
  remediation: string | null;
  remediation_url: string | null;
  count: number;
  resources: ResourceInstance[];
};

type PaginatedGroupedFindings = {
  total_groups: number;
  groups: GroupedFinding[];
};

const DIFF_BADGE: Record<string, string> = {
  new: "bg-emerald-900/50 text-emerald-300 border-emerald-700/50",
  open: "bg-amber-900/50 text-amber-300 border-amber-700/50",
  closed: "bg-slate-800 text-slate-400 border-slate-700",
};

export default function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const qc = useQueryClient();
  const [wsPct, setWsPct] = useState<number | null>(null);
  const [wsStage, setWsStage] = useState<string | null>(null);
  const [tab, setTab] = useState<"findings" | "issues" | "diff" | "logs">("findings");
  const [fSeverity, setFSeverity] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fTriage, setFTriage] = useState("");
  const [fService, setFService] = useState("");
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedDiffFp, setExpandedDiffFp] = useState<string | null>(null);
  const [diffCatFilter, setDiffCatFilter] = useState<string | null>(null);
  const [diffPage, setDiffPage] = useState(0);
  const [diffTriageFilter, setDiffTriageFilter] = useState("");
  const [issueSeverity, setIssueSeverity] = useState("");
  const [issueService, setIssueService] = useState("");
  const [issuesPage, setIssuesPage] = useState(0);
  const [expandedCheckId, setExpandedCheckId] = useState<string | null>(null);

  const scan = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => apiFetch<Scan>(`/api/v1/scans/${scanId}`),
    enabled: !!scanId,
    refetchInterval: (q) => (q.state.data?.status === "running" || q.state.data?.status === "pending" ? 2000 : false),
  });

  const findingsParams = useMemo(() => {
    const p = new URLSearchParams();
    if (fSeverity) p.set("severity", fSeverity);
    if (fStatus) p.set("status", fStatus);
    if (fTriage) p.set("triage", fTriage);
    if (fService) p.set("service", fService);
    p.set("limit", String(PAGE_SIZE));
    p.set("offset", String(page * PAGE_SIZE));
    return p.toString();
  }, [fSeverity, fStatus, fTriage, fService, page]);

  const findings = useQuery({
    queryKey: ["findings", scanId, findingsParams],
    queryFn: () => apiFetch<PaginatedFindings>(`/api/v1/scans/${scanId}/findings?${findingsParams}`),
    enabled: !!scanId && scan.data?.status === "completed",
    staleTime: 0,
    placeholderData: (prev) => prev,
  });

  const services = useQuery({
    queryKey: ["findingServices", scanId],
    queryFn: () => apiFetch<string[]>(`/api/v1/scans/${scanId}/findings/services`),
    enabled: !!scanId && scan.data?.status === "completed",
    staleTime: 60_000,
  });

  const issuesParams = useMemo(() => {
    const p = new URLSearchParams();
    if (issueSeverity) p.set("severity", issueSeverity);
    if (issueService) p.set("service", issueService);
    p.set("limit", String(PAGE_SIZE));
    p.set("offset", String(issuesPage * PAGE_SIZE));
    return p.toString();
  }, [issueSeverity, issueService, issuesPage]);

  const groupedFindings = useQuery({
    queryKey: ["groupedFindings", scanId, issuesParams],
    queryFn: () => apiFetch<PaginatedGroupedFindings>(`/api/v1/scans/${scanId}/findings/grouped?${issuesParams}`),
    enabled: !!scanId && scan.data?.status === "completed",
    staleTime: 0,
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (scan.data?.status === "completed" && scanId) {
      qc.invalidateQueries({ queryKey: ["findings", scanId] });
      qc.invalidateQueries({ queryKey: ["findingServices", scanId] });
      qc.invalidateQueries({ queryKey: ["groupedFindings", scanId] });
    }
  }, [scan.data?.status, scanId, qc]);

  const diffParams = useMemo(() => {
    const p = new URLSearchParams();
    if (diffTriageFilter) p.set("triage", diffTriageFilter);
    return p.toString();
  }, [diffTriageFilter]);

  const diff = useQuery({
    queryKey: ["diff", scanId, diffParams],
    queryFn: () => apiFetch<DiffOut>(`/api/v1/scans/${scanId}/diff${diffParams ? `?${diffParams}` : ""}`),
    enabled: !!scanId && scan.data?.status === "completed",
    retry: false,
  });

  const scanLogs = useQuery({
    queryKey: ["scanLogs", scanId],
    queryFn: () => apiFetch<{ logs: string }>(`/api/v1/scans/${scanId}/logs`),
    enabled: !!scanId,
    refetchInterval:
      scan.data?.status === "running" || scan.data?.status === "pending" ? 2000 : false,
  });

  const patchLabel = useMutation({
    mutationFn: (label: string) =>
      apiFetch<Scan>(`/api/v1/scans/${scanId}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scan", scanId] }),
  });

  const cancelScan = useMutation({
    mutationFn: () => apiFetch<Scan>(`/api/v1/scans/${scanId}/cancel`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan", scanId] });
      qc.invalidateQueries({ queryKey: ["scanLogs", scanId] });
      setWsPct(0);
    },
  });

  const reparseFindings = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean; detail?: string }>(`/api/v1/scans/${scanId}/reparse`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan", scanId] });
      qc.invalidateQueries({ queryKey: ["findings", scanId] });
      qc.invalidateQueries({ queryKey: ["findingServices", scanId] });
      qc.invalidateQueries({ queryKey: ["groupedFindings", scanId] });
      qc.invalidateQueries({ queryKey: ["diff", scanId] });
      qc.invalidateQueries({ queryKey: ["scanLogs", scanId] });
    },
  });

  const triage = useMutation({
    mutationFn: (vars: { clientId: string; fingerprint: string; state: string }) =>
      apiFetch(`/api/v1/clients/${vars.clientId}/triage/${vars.fingerprint}`, {
        method: "PUT",
        body: JSON.stringify({ state: vars.state }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings", scanId] });
      qc.invalidateQueries({ queryKey: ["groupedFindings", scanId] });
    },
  });

  const base = import.meta.env.VITE_API_URL || "";
  const wsUrl = useMemo(() => {
    if (!scanId) return null;
    const tok = getToken();
    if (!tok) return null;
    const path = `/api/v1/ws/scans/${scanId}?token=${encodeURIComponent(tok)}`;
    if (base) {
      const u = new URL(base);
      const wsProto = u.protocol === "https:" ? "wss" : "ws";
      return `${wsProto}://${u.host}${path}`;
    }
    const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${wsProto}://${window.location.host}${path}`;
  }, [scanId, base]);

  useEffect(() => {
    if (!wsUrl || !scanId) return;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
      try {
        const p = JSON.parse(ev.data as string);
        if (typeof p.pct === "number") setWsPct(p.pct);
        if (typeof p.stage === "string") setWsStage(p.stage);
        // Scan row is marked ``completed`` before parse_findings runs; refresh findings when ingest catches up.
        if (p.stage === "diff" || p.stage === "completed") {
          qc.invalidateQueries({ queryKey: ["findings", scanId] });
          qc.invalidateQueries({ queryKey: ["findingServices", scanId] });
          qc.invalidateQueries({ queryKey: ["groupedFindings", scanId] });
          qc.invalidateQueries({ queryKey: ["diff", scanId] });
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, [wsUrl, scanId, qc]);

  const [labelEdit, setLabelEdit] = useState("");
  useEffect(() => {
    if (scan.data?.label != null) setLabelEdit(scan.data.label);
  }, [scan.data?.label]);

  if (!scanId) return null;

  const pct = wsPct ?? scan.data?.progress_pct ?? 0;
  const stageLabel = wsStage;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <Link to={`/clients/${scan.data?.client_id ?? ""}`} className="text-sm text-emerald-400 hover:underline">
        ← Client
      </Link>
      {scan.data && (
        <header className="mt-4 space-y-2">
          <h1 className="text-2xl font-semibold">Scan</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
            <span className="rounded-full border border-slate-700 px-2 py-0.5 font-mono text-xs">{scan.data.status}</span>
            <span>{pct}%</span>
            {stageLabel && (
              <span className="rounded-full border border-slate-600 px-2 py-0.5 font-mono text-xs text-slate-300">
                {stageLabel.replace(/_/g, " ")}
              </span>
            )}
            {scan.data.error_message && <span className="text-red-400">{scan.data.error_message}</span>}
            {scan.data.status === "completed" && typeof scan.data.findings_count === "number" && (
              <span className="text-slate-500">Findings in DB: {scan.data.findings_count}</span>
            )}
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={labelEdit}
              onChange={(e) => setLabelEdit(e.target.value)}
              placeholder="Scan label"
            />
            <button
              type="button"
              className="rounded-lg bg-slate-700 px-3 py-2 text-sm"
              onClick={() => patchLabel.mutate(labelEdit)}
            >
              Save label
            </button>
            {(scan.data.status === "pending" || scan.data.status === "running") && (
              <button
                type="button"
                className="rounded-lg border border-amber-700/60 bg-amber-950/40 px-3 py-2 text-sm text-amber-200 hover:bg-amber-950/70 disabled:opacity-50"
                disabled={cancelScan.isPending}
                onClick={() => cancelScan.mutate()}
              >
                Cancel scan
              </button>
            )}
            {cancelScan.isError && (
              <span className="text-sm text-red-400">{cancelScan.error.message}</span>
            )}
            {scan.data.status === "completed" && (
              <button
                type="button"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                disabled={reparseFindings.isPending}
                onClick={() => reparseFindings.mutate()}
              >
                Re-parse findings
              </button>
            )}
            {reparseFindings.isError && (
              <span className="text-sm text-red-400">{reparseFindings.error.message}</span>
            )}
            <a
              className="rounded-lg bg-emerald-700 px-3 py-2 text-sm text-white"
              href={`${base || ""}/api/v1/scans/${scanId}/export.xlsx`}
              onClick={(e) => {
                e.preventDefault();
                const url = `${base || ""}/api/v1/scans/${scanId}/export.xlsx`;
                fetch(url, {
                  headers: { Authorization: `Bearer ${getToken()}` },
                })
                  .then((r) => r.blob())
                  .then((b) => {
                    const url = URL.createObjectURL(b);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `scan-${scanId}.xlsx`;
                    a.click();
                    URL.revokeObjectURL(url);
                  });
              }}
            >
              Export Excel
            </a>
          </div>
        </header>
      )}

      <div className="mt-6 flex gap-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          className={`rounded-lg px-3 py-1 text-sm ${tab === "findings" ? "bg-slate-800" : "text-slate-400"}`}
          onClick={() => setTab("findings")}
        >
          Findings
        </button>
        <button
          type="button"
          className={`rounded-lg px-3 py-1 text-sm ${tab === "issues" ? "bg-slate-800" : "text-slate-400"}`}
          onClick={() => setTab("issues")}
        >
          Issues
        </button>
        <button
          type="button"
          className={`rounded-lg px-3 py-1 text-sm ${tab === "diff" ? "bg-slate-800" : "text-slate-400"}`}
          onClick={() => setTab("diff")}
        >
          Diff
        </button>
        <button
          type="button"
          className={`rounded-lg px-3 py-1 text-sm ${tab === "logs" ? "bg-slate-800" : "text-slate-400"}`}
          onClick={() => setTab("logs")}
        >
          Logs
        </button>
      </div>

      {tab === "findings" && (
        <div className="mt-4">
          {/* Filter bar */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={fSeverity}
              onChange={(e) => { setFSeverity(e.target.value); setPage(0); }}
            >
              <option value="">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={fStatus}
              onChange={(e) => { setFStatus(e.target.value); setPage(0); }}
            >
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={fTriage}
              onChange={(e) => { setFTriage(e.target.value); setPage(0); }}
            >
              <option value="">All triage</option>
              <option value="none">Untriaged</option>
              <option value="valid">Valid</option>
              <option value="false_positive">False positive</option>
              <option value="not_applicable">N/A</option>
            </select>
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={fService}
              onChange={(e) => { setFService(e.target.value); setPage(0); }}
            >
              <option value="">All services</option>
              {services.data?.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {(fSeverity || fStatus || fTriage || fService) && (
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200"
                onClick={() => { setFSeverity(""); setFStatus(""); setFTriage(""); setFService(""); setPage(0); }}
              >
                Clear filters
              </button>
            )}
            {findings.data && (
              <span className="ml-auto text-xs text-slate-500">
                {findings.data.total} finding{findings.data.total !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="w-6 py-2" />
                  <th className="py-2 pr-3">Severity</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Triage</th>
                  <th className="py-2 pr-3">Service</th>
                  <th className="py-2 pr-3">Resource</th>
                  <th className="py-2">Description</th>
                </tr>
              </thead>
              <tbody>
                {findings.data?.items.map((f) => {
                  const open = expandedId === f.id;
                  return (
                    <Fragment key={f.id}>
                      <tr
                        className="border-b border-slate-900 hover:bg-slate-900/40 cursor-pointer"
                        onClick={() => setExpandedId(open ? null : f.id)}
                      >
                        <td className="py-2 pl-1 pr-1 text-slate-500">
                          <svg className={`h-4 w-4 transition-transform ${open ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                          </svg>
                        </td>
                        <td className="py-2 pr-3">
                          <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${SEV_BADGE[f.severity] ?? "text-slate-300"}`}>
                            {f.severity}
                          </span>
                        </td>
                        <td className="py-2 pr-3 text-slate-300">{f.status}</td>
                        <td className="py-2 pr-3" onClick={(e) => e.stopPropagation()}>
                          <select
                            className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
                            value={f.triage ?? ""}
                            onChange={(e) => {
                              const v = e.target.value;
                              if (!v || !scan.data?.client_id) return;
                              triage.mutate({ clientId: scan.data.client_id, fingerprint: f.fingerprint, state: v });
                            }}
                          >
                            <option value="">—</option>
                            <option value="valid">Valid</option>
                            <option value="false_positive">False positive</option>
                            <option value="not_applicable">N/A</option>
                          </select>
                        </td>
                        <td className="py-2 pr-3 font-mono text-xs text-slate-300">{f.service}</td>
                        <td className="max-w-[14rem] truncate py-2 pr-3 font-mono text-xs text-slate-400">{f.resource_id}</td>
                        <td className="max-w-md truncate py-2 text-slate-400">{f.description}</td>
                      </tr>
                      {open && (
                        <tr className="border-b border-slate-900 bg-slate-900/20">
                          <td colSpan={7} className="px-4 py-3">
                            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-xs">
                              <dt className="text-slate-500">Description</dt>
                              <dd className="text-slate-300 whitespace-pre-wrap">{f.description ?? "—"}</dd>
                              <dt className="text-slate-500">Resource</dt>
                              <dd className="font-mono text-slate-300 break-all">{f.resource_id}</dd>
                              <dt className="text-slate-500">Check ID</dt>
                              <dd className="font-mono text-slate-300">{f.check_id}</dd>
                              <dt className="text-slate-500">Region</dt>
                              <dd className="text-slate-300">{f.region || "—"}</dd>
                              <dt className="text-slate-500">Compliance</dt>
                              <dd className="text-slate-300">{f.compliance_framework || "—"}</dd>
                              <dt className="text-slate-500">Remediation</dt>
                              <dd className="text-slate-300 whitespace-pre-wrap">
                                {f.remediation?.replace(/\*\*/g, "") || "—"}
                                {f.remediation_url && (
                                  <>
                                    {" "}
                                    <a href={f.remediation_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">
                                      Reference
                                    </a>
                                  </>
                                )}
                              </dd>
                              <dt className="text-slate-500">Fingerprint</dt>
                              <dd className="font-mono text-slate-400">{f.fingerprint}</dd>
                            </dl>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {findings.data && findings.data.total > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </button>
              <span className="text-slate-500">
                Page {page + 1} of {Math.ceil(findings.data.total / PAGE_SIZE)}
              </span>
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                disabled={(page + 1) * PAGE_SIZE >= findings.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}

          {scan.data?.status === "cancelled" && (
            <p className="mt-4 text-slate-500">This scan was cancelled; there are no findings.</p>
          )}
          {scan.data?.status !== "completed" && scan.data?.status !== "cancelled" && (
            <p className="mt-4 text-slate-500">Findings appear when the scan completes.</p>
          )}
        </div>
      )}

      {tab === "issues" && (
        <div className="mt-4">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={issueSeverity}
              onChange={(e) => { setIssueSeverity(e.target.value); setIssuesPage(0); }}
            >
              <option value="">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
              value={issueService}
              onChange={(e) => { setIssueService(e.target.value); setIssuesPage(0); }}
            >
              <option value="">All services</option>
              {services.data?.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {(issueSeverity || issueService) && (
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200"
                onClick={() => { setIssueSeverity(""); setIssueService(""); setIssuesPage(0); }}
              >
                Clear filters
              </button>
            )}
            {groupedFindings.data && (
              <span className="ml-auto text-xs text-slate-500">
                {groupedFindings.data.total_groups} issue type{groupedFindings.data.total_groups !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="w-6 py-2" />
                  <th className="py-2 pr-3">Severity</th>
                  <th className="py-2 pr-3">Service</th>
                  <th className="py-2 pr-3">Description</th>
                  <th className="py-2 pr-3 text-right">Instances</th>
                </tr>
              </thead>
              <tbody>
                {groupedFindings.data?.groups.map((g) => {
                  const open = expandedCheckId === g.check_id;
                  return (
                    <Fragment key={g.check_id}>
                      <tr
                        className="border-b border-slate-900 hover:bg-slate-900/40 cursor-pointer"
                        onClick={() => setExpandedCheckId(open ? null : g.check_id)}
                      >
                        <td className="py-2 pl-1 pr-1 text-slate-500">
                          <svg className={`h-4 w-4 transition-transform ${open ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                          </svg>
                        </td>
                        <td className="py-2 pr-3">
                          <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${SEV_BADGE[g.severity] ?? "text-slate-300"}`}>
                            {g.severity}
                          </span>
                        </td>
                        <td className="py-2 pr-3 font-mono text-xs text-slate-300">{g.service}</td>
                        <td className="max-w-lg truncate py-2 pr-3 text-slate-400">{g.description}</td>
                        <td className="py-2 pr-3 text-right">
                          <span className="inline-block rounded-full bg-slate-800 border border-slate-700 px-2.5 py-0.5 text-xs font-semibold text-slate-200">
                            {g.count}
                          </span>
                        </td>
                      </tr>
                      {open && (
                        <tr className="border-b border-slate-900 bg-slate-900/20">
                          <td colSpan={5} className="px-4 py-3">
                            <div className="mb-2">
                              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-xs">
                                <dt className="text-slate-500">Check ID</dt>
                                <dd className="font-mono text-slate-300">{g.check_id}</dd>
                                <dt className="text-slate-500">Remediation</dt>
                                <dd className="text-slate-300 whitespace-pre-wrap">
                                  {g.remediation?.replace(/\*\*/g, "") || "—"}
                                  {g.remediation_url && (
                                    <>
                                      {" "}
                                      <a href={g.remediation_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">
                                        Reference
                                      </a>
                                    </>
                                  )}
                                </dd>
                              </dl>
                            </div>
                            <table className="w-full border-collapse text-left text-xs">
                              <thead>
                                <tr className="border-b border-slate-800 text-slate-500">
                                  <th className="py-1.5 pr-3">Resource</th>
                                  <th className="py-1.5 pr-3">Region</th>
                                  <th className="py-1.5 pr-3">Status</th>
                                  <th className="py-1.5 pr-3">Triage</th>
                                </tr>
                              </thead>
                              <tbody>
                                {g.resources.map((r) => (
                                  <tr key={r.id} className="border-b border-slate-900/50">
                                    <td className="max-w-xs truncate py-1.5 pr-3 font-mono text-slate-300">{r.resource_id}</td>
                                    <td className="py-1.5 pr-3 text-slate-400">{r.region || "—"}</td>
                                    <td className="py-1.5 pr-3 text-slate-400">{r.status}</td>
                                    <td className="py-1.5 pr-3" onClick={(e) => e.stopPropagation()}>
                                      <select
                                        className="rounded border border-slate-700 bg-slate-950 px-2 py-0.5 text-xs"
                                        value={r.triage ?? ""}
                                        onChange={(e) => {
                                          const v = e.target.value;
                                          if (!v || !scan.data?.client_id) return;
                                          triage.mutate({ clientId: scan.data.client_id, fingerprint: r.fingerprint, state: v });
                                        }}
                                      >
                                        <option value="">—</option>
                                        <option value="valid">Valid</option>
                                        <option value="false_positive">False positive</option>
                                        <option value="not_applicable">N/A</option>
                                      </select>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {groupedFindings.data && groupedFindings.data.total_groups > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                disabled={issuesPage === 0}
                onClick={() => setIssuesPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </button>
              <span className="text-slate-500">
                Page {issuesPage + 1} of {Math.ceil(groupedFindings.data.total_groups / PAGE_SIZE)}
              </span>
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                disabled={(issuesPage + 1) * PAGE_SIZE >= groupedFindings.data.total_groups}
                onClick={() => setIssuesPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}

          {scan.data?.status !== "completed" && scan.data?.status !== "cancelled" && (
            <p className="mt-4 text-slate-500">Issues appear when the scan completes.</p>
          )}
        </div>
      )}

      {tab === "diff" && (
        <div className="mt-4 space-y-4">
          {diff.isError && <p className="text-slate-500">Diff not ready or no comparison scan.</p>}
          {diff.data && (
            <>
              <div className="flex flex-wrap items-center gap-3">
                {Object.entries(diff.data.counts).map(([cat, n]) => {
                  const active = diffCatFilter === cat;
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => { setDiffCatFilter(active ? null : cat); setDiffPage(0); }}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all ${DIFF_BADGE[cat] ?? "text-slate-300"} ${active ? "ring-2 ring-slate-400 ring-offset-1 ring-offset-slate-950 scale-105" : "opacity-80 hover:opacity-100"}`}
                    >
                      {cat} <span className="font-semibold">{n}</span>
                    </button>
                  );
                })}
                {diffCatFilter && (
                  <button
                    type="button"
                    className="text-xs text-slate-500 hover:text-slate-300"
                    onClick={() => { setDiffCatFilter(null); setDiffPage(0); }}
                  >
                    Show all
                  </button>
                )}
                <select
                  className="ml-auto rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
                  value={diffTriageFilter}
                  onChange={(e) => { setDiffTriageFilter(e.target.value); setDiffPage(0); setDiffCatFilter(null); }}
                >
                  <option value="">All triage</option>
                  <option value="valid">Valid only</option>
                  <option value="false_positive">False positive only</option>
                  <option value="not_applicable">N/A only</option>
                  <option value="none">Untriaged only</option>
                </select>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="w-6 py-2" />
                      <th className="py-2 pr-3">Change</th>
                      <th className="py-2 pr-3">Severity</th>
                      <th className="py-2 pr-3">Service</th>
                      <th className="py-2 pr-3">Resource</th>
                      <th className="py-2 pr-3">Triage</th>
                      <th className="py-2">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const filtered = diffCatFilter ? diff.data.items.filter((i) => i.category === diffCatFilter) : diff.data.items;
                      return filtered.slice(diffPage * PAGE_SIZE, (diffPage + 1) * PAGE_SIZE).map((i) => {
                        const key = `${i.category}-${i.fingerprint}`;
                        const open = expandedDiffFp === key;
                        return (
                          <Fragment key={key}>
                            <tr
                              className="border-b border-slate-900 hover:bg-slate-900/40 cursor-pointer"
                              onClick={() => setExpandedDiffFp(open ? null : key)}
                            >
                              <td className="py-2 pl-1 pr-1 text-slate-500">
                                <svg className={`h-4 w-4 transition-transform ${open ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                                </svg>
                              </td>
                              <td className="py-2 pr-3">
                                <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${DIFF_BADGE[i.category] ?? "text-slate-300"}`}>
                                  {i.category}
                                </span>
                              </td>
                              <td className="py-2 pr-3">
                                {i.severity ? (
                                  <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${SEV_BADGE[i.severity] ?? "text-slate-300"}`}>
                                    {i.severity}
                                  </span>
                                ) : (
                                  <span className="text-xs text-slate-600">--</span>
                                )}
                              </td>
                              <td className="py-2 pr-3 font-mono text-xs text-slate-300">{i.service ?? "--"}</td>
                              <td className="max-w-[14rem] truncate py-2 pr-3 font-mono text-xs text-slate-400">
                                {i.resource_id ?? i.fingerprint.slice(0, 16) + "..."}
                              </td>
                              <td className="py-2 pr-3 text-xs text-slate-400">{i.triage?.replace(/_/g, " ") ?? "—"}</td>
                              <td className="max-w-md truncate py-2 text-slate-400">
                                {i.description ?? "--"}
                              </td>
                            </tr>
                            {open && (
                              <tr className="border-b border-slate-900 bg-slate-900/20">
                                <td colSpan={7} className="px-4 py-3">
                                  <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-xs">
                                    <dt className="text-slate-500">Description</dt>
                                    <dd className="text-slate-300 whitespace-pre-wrap">{i.description ?? "—"}</dd>
                                    <dt className="text-slate-500">Resource</dt>
                                    <dd className="font-mono text-slate-300 break-all">{i.resource_id ?? "—"}</dd>
                                    <dt className="text-slate-500">Check ID</dt>
                                    <dd className="font-mono text-slate-300">{i.check_id ?? "—"}</dd>
                                    <dt className="text-slate-500">Remediation</dt>
                                    <dd className="text-slate-300 whitespace-pre-wrap">
                                      {i.remediation?.replace(/\*\*/g, "") || "—"}
                                      {i.remediation_url && (
                                        <>
                                          {" "}
                                          <a href={i.remediation_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">
                                            Reference
                                          </a>
                                        </>
                                      )}
                                    </dd>
                                    <dt className="text-slate-500">Fingerprint</dt>
                                    <dd className="font-mono text-slate-400">{i.fingerprint}</dd>
                                  </dl>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      });
                    })()}
                  </tbody>
                </table>
              </div>
              {(() => {
                const filtered = diffCatFilter ? diff.data.items.filter((i) => i.category === diffCatFilter) : diff.data.items;
                const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
                return filtered.length > PAGE_SIZE ? (
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <button
                      type="button"
                      className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                      disabled={diffPage === 0}
                      onClick={() => setDiffPage((p) => Math.max(0, p - 1))}
                    >
                      Previous
                    </button>
                    <span className="text-slate-500">
                      Page {diffPage + 1} of {totalPages}
                    </span>
                    <button
                      type="button"
                      className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                      disabled={diffPage + 1 >= totalPages}
                      onClick={() => setDiffPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                ) : null;
              })()}
            </>
          )}
        </div>
      )}

      {tab === "logs" && (
        <div className="mt-4">
          {scanLogs.isError && <p className="text-sm text-red-400">Could not load logs.</p>}
          <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-all rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-300">
            {scanLogs.data?.logs || (scan.data?.status === "pending" || scan.data?.status === "running" ? "…" : "")}
          </pre>
          {(scan.data?.status === "pending" || scan.data?.status === "running") && (
            <p className="mt-2 text-xs text-slate-500">Logs refresh every 2s while the scan is active.</p>
          )}
        </div>
      )}
    </div>
  );
}
