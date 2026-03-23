import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";

type Cloud = "aws" | "azure" | "gcp";

type Credential = {
  id: string;
  label: string;
  provider: string;
  auth_method: string;
  created_at: string;
};

type Scan = {
  id: string;
  label: string | null;
  status: string;
  progress_pct: number;
  created_at: string;
};

type Dashboard = {
  scan_id: string | null;
  total_findings: number;
  by_severity: Record<string, number>;
  by_service: Record<string, number>;
  diff_counts: Record<string, number> | null;
};

type Client = { id: string; name: string; description: string | null };

const CLOUDS: { id: Cloud; label: string; short: string }[] = [
  { id: "aws", label: "Amazon Web Services", short: "AWS" },
  { id: "azure", label: "Microsoft Azure", short: "Azure" },
  { id: "gcp", label: "Google Cloud", short: "GCP" },
];

const SEV_CLS: Record<string, string> = {
  critical: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/60 dark:text-red-300 dark:border-red-700/50",
  high: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/50 dark:text-orange-300 dark:border-orange-700/50",
  medium: "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-700/40",
  low: "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/40 dark:text-sky-300 dark:border-sky-700/40",
};

const DIFF_CLS: Record<string, string> = {
  new: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-300 dark:border-emerald-700/50",
  open: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/50 dark:text-amber-300 dark:border-amber-700/50",
  closed: "bg-surface-alt text-content-muted border-edge",
};

export default function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const nav = useNavigate();
  const qc = useQueryClient();

  const [cloud, setCloud] = useState<Cloud>("aws");
  const [ak, setAk] = useState("");
  const [sk, setSk] = useState("");
  const [azureTenant, setAzureTenant] = useState("");
  const [azureClientId, setAzureClientId] = useState("");
  const [azureSecret, setAzureSecret] = useState("");
  const [gcpJson, setGcpJson] = useState("");
  const [credLabel, setCredLabel] = useState("default");
  const [scanLabel, setScanLabel] = useState("");
  const [credId, setCredId] = useState("");
  const [prevScanId, setPrevScanId] = useState("");

  const [editClientOpen, setEditClientOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [deleteClientOpen, setDeleteClientOpen] = useState(false);
  const [credentialSelectInitialized, setCredentialSelectInitialized] = useState(false);

  const client = useQuery({
    queryKey: ["client", clientId],
    queryFn: () => apiFetch<Client>(`/api/v1/clients/${clientId}`),
    enabled: !!clientId,
  });

  const creds = useQuery({
    queryKey: ["creds", clientId],
    queryFn: () => apiFetch<Credential[]>(`/api/v1/clients/${clientId}/credentials`),
    enabled: !!clientId,
  });

  const scans = useQuery({
    queryKey: ["scans", clientId],
    queryFn: () => apiFetch<Scan[]>(`/api/v1/clients/${clientId}/scans`),
    enabled: !!clientId,
    refetchInterval: 4000,
  });

  const dashboard = useQuery({
    queryKey: ["dash", clientId],
    queryFn: () => apiFetch<Dashboard>(`/api/v1/clients/${clientId}/dashboard`),
    enabled: !!clientId,
    refetchInterval: 5000,
  });

  const updateClient = useMutation({
    mutationFn: (body: { name?: string; description?: string }) =>
      apiFetch<Client>(`/api/v1/clients/${clientId}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["client", clientId] });
      qc.invalidateQueries({ queryKey: ["clients"] });
      setEditClientOpen(false);
    },
  });

  const deleteClient = useMutation({
    mutationFn: () => apiFetch<void>(`/api/v1/clients/${clientId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clients"] });
      nav("/");
    },
  });

  function openEditClient() {
    if (!client.data) return;
    setEditName(client.data.name);
    setEditDesc(client.data.description ?? "");
    setEditClientOpen(true);
  }

  const addCred = useMutation({
    mutationFn: () => {
      const label = credLabel || "default";
      if (cloud === "aws") {
        return apiFetch<Credential>(`/api/v1/clients/${clientId}/credentials`, {
          method: "POST",
          body: JSON.stringify({
            label,
            provider: "aws",
            auth_method: "static_keys",
            aws_static: { access_key_id: ak, secret_access_key: sk },
          }),
        });
      }
      if (cloud === "azure") {
        return apiFetch<Credential>(`/api/v1/clients/${clientId}/credentials`, {
          method: "POST",
          body: JSON.stringify({
            label,
            provider: "azure",
            auth_method: "static_keys",
            azure_sp: {
              tenant_id: azureTenant,
              client_id: azureClientId,
              client_secret: azureSecret,
            },
          }),
        });
      }
      return apiFetch<Credential>(`/api/v1/clients/${clientId}/credentials`, {
        method: "POST",
        body: JSON.stringify({
          label,
          provider: "gcp",
          auth_method: "static_keys",
          gcp_sa: { service_account_json: gcpJson },
        }),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["creds", clientId] });
      setAk("");
      setSk("");
      setAzureTenant("");
      setAzureClientId("");
      setAzureSecret("");
      setGcpJson("");
    },
  });

  const deleteCred = useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/credentials/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["creds", clientId] }),
  });

  const startScan = useMutation({
    mutationFn: () =>
      apiFetch<Scan>(`/api/v1/clients/${clientId}/scans`, {
        method: "POST",
        body: JSON.stringify({
          credential_id: credId,
          label: scanLabel || null,
          previous_scan_id: prevScanId || null,
        }),
      }),
    onSuccess: (s) => nav(`/scans/${s.id}`),
  });

  const selectedCred = creds.data?.find((c) => c.id === credId);
  const scanAwsOnly = selectedCred && selectedCred.provider !== "aws";

  const completedScans = useMemo(
    () => scans.data?.filter((s) => s.status === "completed") ?? [],
    [scans.data],
  );

  useEffect(() => {
    if (credentialSelectInitialized || !creds.data?.length) return;
    const firstAws = creds.data.find((c) => c.provider === "aws");
    if (firstAws) setCredId(firstAws.id);
    setCredentialSelectInitialized(true);
  }, [creds.data, credentialSelectInitialized]);

  const credSaveDisabled =
    addCred.isPending ||
    (cloud === "aws" && (!ak || !sk)) ||
    (cloud === "azure" && (!azureTenant || !azureClientId || !azureSecret)) ||
    (cloud === "gcp" && !gcpJson.trim());

  if (!clientId) return null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:max-w-5xl xl:max-w-6xl sm:px-6">
      <Link to="/" className="text-sm text-emerald-600 hover:underline dark:text-emerald-400">
        ← Clients
      </Link>
      {client.data && (
        <header className="mt-4 mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{client.data.name}</h1>
            {client.data.description && <p className="text-content-muted">{client.data.description}</p>}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-edge px-3 py-1.5 text-sm text-content hover:bg-surface-alt"
              onClick={openEditClient}
            >
              Edit client
            </button>
            <button
              type="button"
              className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-900/60 dark:text-red-400 dark:hover:bg-red-950/40"
              onClick={() => setDeleteClientOpen(true)}
            >
              Delete client
            </button>
          </div>
        </header>
      )}

      <section className="mb-8 rounded-xl border border-edge-soft bg-surface/40 p-4">
        <h2 className="mb-3 text-lg font-medium">Dashboard</h2>
        {dashboard.data && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-edge-soft p-3">
              <div className="text-xs uppercase text-content-faint">Total findings</div>
              <div className="text-2xl font-semibold">{dashboard.data.total_findings}</div>
            </div>
            <div className="rounded-lg border border-edge-soft p-3">
              <div className="mb-2 text-xs uppercase text-content-faint">By severity</div>
              <div className="flex flex-wrap gap-2">
                {(["critical", "high", "medium", "low"] as const).map((sev) => {
                  const n = dashboard.data!.by_severity[sev] ?? 0;
                  return (
                    <span key={sev} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${SEV_CLS[sev]}`}>
                      {sev} <span className="font-semibold">{n}</span>
                    </span>
                  );
                })}
              </div>
            </div>
            {dashboard.data.diff_counts && (
              <div className="rounded-lg border border-edge-soft p-3 sm:col-span-2">
                <div className="mb-2 text-xs uppercase text-content-faint">Diff (latest scan)</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(dashboard.data.diff_counts).map(([cat, n]) => (
                    <span key={cat} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${DIFF_CLS[cat] ?? "text-content-secondary"}`}>
                      {cat} <span className="font-semibold">{n}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="mb-8 rounded-xl border border-edge-soft bg-surface/40 p-4">
        <h2 className="mb-1 text-lg font-medium">Cloud credentials</h2>
        <p className="mb-4 text-sm text-content-faint">
          Choose a provider, then enter secrets. They are encrypted on the server. Prowler scans in this build run on{" "}
          <span className="text-content-secondary">AWS credentials only</span>; Azure and GCP entries are stored for upcoming
          scan support and workflows.
        </p>

        <div className="mb-4 flex flex-wrap gap-2">
          {CLOUDS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCloud(c.id)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                cloud === c.id
                  ? "bg-emerald-600 text-white"
                  : "border border-edge bg-field text-content-secondary hover:border-content-faint"
              }`}
            >
              {c.short}
            </button>
          ))}
        </div>
        <p className="mb-4 text-xs text-content-faint">{CLOUDS.find((c) => c.id === cloud)?.label}</p>

        <div className="grid gap-3">
          <input
            className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
            placeholder="Credential label (e.g. prod, staging)"
            value={credLabel}
            onChange={(e) => setCredLabel(e.target.value)}
          />

          {cloud === "aws" && (
            <>
              <input
                className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                placeholder="AWS access key ID"
                value={ak}
                onChange={(e) => setAk(e.target.value)}
                autoComplete="off"
              />
              <input
                className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                placeholder="AWS secret access key"
                type="password"
                value={sk}
                onChange={(e) => setSk(e.target.value)}
                autoComplete="off"
              />
            </>
          )}

          {cloud === "azure" && (
            <>
              <input
                className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                placeholder="Directory (tenant) ID"
                value={azureTenant}
                onChange={(e) => setAzureTenant(e.target.value)}
              />
              <input
                className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                placeholder="Application (client) ID"
                value={azureClientId}
                onChange={(e) => setAzureClientId(e.target.value)}
              />
              <input
                className="rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                placeholder="Client secret"
                type="password"
                value={azureSecret}
                onChange={(e) => setAzureSecret(e.target.value)}
              />
            </>
          )}

          {cloud === "gcp" && (
            <textarea
              className="min-h-[160px] w-full rounded-lg border border-edge bg-field px-3 py-2 font-mono text-xs text-content"
              placeholder='Paste service account JSON (e.g. { "type": "service_account", "project_id": "..." })'
              value={gcpJson}
              onChange={(e) => setGcpJson(e.target.value)}
            />
          )}
        </div>
        <button
          type="button"
          className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          disabled={credSaveDisabled}
          onClick={() => addCred.mutate()}
        >
          Save credential
        </button>

        <ul className="mt-4 space-y-2 text-sm">
          {creds.data?.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-2 rounded border border-edge-soft px-3 py-2"
            >
              <span>
                <span className="mr-2 rounded bg-surface-alt px-1.5 py-0.5 text-xs uppercase text-emerald-600 dark:text-emerald-300">
                  {c.provider}
                </span>
                {c.label} · {c.auth_method}
              </span>
              <div className="flex items-center gap-2">
                <span className="hidden font-mono text-xs text-content-faint sm:inline">{c.id.slice(0, 8)}…</span>
                <button
                  type="button"
                  className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                  onClick={() => {
                    if (window.confirm("Remove this credential?")) deleteCred.mutate(c.id);
                  }}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-edge-soft bg-surface/40 p-4">
        <h2 className="mb-3 text-lg font-medium">Start audit</h2>
        <p className="mb-3 text-sm text-content-faint">
          Prowler execution is wired for <strong className="text-content-secondary">AWS</strong> today. Pick an AWS credential
          below; Azure/GCP credentials cannot start a scan until the worker adds those providers.
        </p>
        <div className="grid gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-content-muted">Credential</label>
            <select
              className="w-full rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
              value={credId}
              onChange={(e) => setCredId(e.target.value)}
            >
              <option value="">Select a credential…</option>
              {creds.data?.map((c) => (
                <option key={c.id} value={c.id} disabled={c.provider !== "aws"}>
                  {c.label} ({c.provider})
                  {c.provider !== "aws" ? " — Prowler scan not available yet" : ""}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-content-faint">
              Values are the saved credential IDs. AWS entries can run Prowler; others are disabled.
            </p>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-content-muted">Scan label</label>
            <input
              className="w-full rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
              placeholder="e.g. Initial scan"
              value={scanLabel}
              onChange={(e) => setScanLabel(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-content-muted">
              Compare to previous scan (optional)
            </label>
            <select
              className="w-full rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
              value={prevScanId}
              onChange={(e) => setPrevScanId(e.target.value)}
            >
              <option value="">None — no diff baseline</option>
              {completedScans.map((s) => (
                <option key={s.id} value={s.id}>
                  {(s.label || "Scan") + " · " + s.id.slice(0, 8)}… ({s.status})
                </option>
              ))}
            </select>
          </div>
        </div>
        {scanAwsOnly && (
          <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">Selected credential is not AWS — scan will fail. Choose an aws credential.</p>
        )}
        <button
          type="button"
          className="mt-3 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
          disabled={startScan.isPending || !credId || !!scanAwsOnly}
          onClick={() => startScan.mutate()}
        >
          Start Prowler scan (AWS)
        </button>
        <ul className="mt-6 space-y-2 text-sm">
          {scans.data?.map((s) => (
            <li key={s.id}>
              <Link className="text-sky-600 hover:underline dark:text-sky-400" to={`/scans/${s.id}`}>
                {s.label || "Scan"} ·{" "}
                <span className={s.status === "cancelled" ? "text-amber-600 dark:text-amber-400/90" : ""}>{s.status}</span> ·{" "}
                {s.progress_pct}%
              </Link>
              <span className="ml-2 font-mono text-xs text-content-faint">{s.id}</span>
            </li>
          ))}
        </ul>
      </section>

      {editClientOpen && client.data && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-edge bg-surface p-6 shadow-xl">
            <h2 className="text-lg font-semibold">Edit client</h2>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs text-content-muted">Name</label>
                <input
                  className="mt-1 w-full rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-content-muted">Description</label>
                <input
                  className="mt-1 w-full rounded-lg border border-edge bg-field px-3 py-2 text-sm text-content"
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-content-muted hover:text-content"
                onClick={() => setEditClientOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                disabled={updateClient.isPending || !editName.trim()}
                onClick={() =>
                  updateClient.mutate({ name: editName.trim(), description: editDesc.trim() || undefined })
                }
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteClientOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-edge bg-surface p-6 shadow-xl">
            <h2 className="text-lg font-semibold">Delete this client?</h2>
            <p className="mt-2 text-sm text-content-muted">All credentials and scans for this client will be removed.</p>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-content-muted hover:text-content"
                onClick={() => setDeleteClientOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
                disabled={deleteClient.isPending}
                onClick={() => deleteClient.mutate()}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
