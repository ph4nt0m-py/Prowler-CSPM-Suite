import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";

type Client = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
};

export default function ClientsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["clients"],
    queryFn: () => apiFetch<Client[]>("/api/v1/clients"),
  });
  const create = useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      apiFetch<Client>("/api/v1/clients", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { name?: string; description?: string } }) =>
      apiFetch<Client>(`/api/v1/clients/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clients"] });
      setEditing(null);
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/clients/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });

  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [editing, setEditing] = useState<Client | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Client | null>(null);

  function openEdit(c: Client) {
    setEditing(c);
    setEditName(c.name);
    setEditDesc(c.description ?? "");
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Clients</h1>
          <p className="text-sm text-slate-400">Create a client, choose a cloud on the next screen, add credentials, then run audits.</p>
        </div>
      </header>

      <form
        className="mb-8 flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          create.mutate({ name: name.trim(), description: desc.trim() || undefined });
          setName("");
          setDesc("");
        }}
      >
        <div className="flex-1 space-y-1">
          <label className="text-xs font-medium text-slate-400">Name</label>
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Corp"
          />
        </div>
        <div className="flex-1 space-y-1">
          <label className="text-xs font-medium text-slate-400">Description</label>
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Optional"
          />
        </div>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          Create
        </button>
      </form>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      <ul className="space-y-2">
        {data?.map((c) => (
          <li
            key={c.id}
            className="flex items-stretch gap-0 overflow-hidden rounded-lg border border-slate-800 bg-slate-900/40"
          >
            <Link
              to={`/clients/${c.id}`}
              className="min-w-0 flex-1 px-4 py-3 transition hover:bg-slate-900/80"
            >
              <div className="font-medium">{c.name}</div>
              {c.description && <div className="text-sm text-slate-400">{c.description}</div>}
            </Link>
            <div className="flex shrink-0 flex-col justify-center gap-1 border-l border-slate-800 bg-slate-950/50 px-2 py-2">
              <button
                type="button"
                className="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
                onClick={() => openEdit(c)}
              >
                Edit
              </button>
              <button
                type="button"
                className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-950/50 hover:text-red-300"
                onClick={() => setDeleteTarget(c)}
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
            <h2 className="text-lg font-semibold">Edit client</h2>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs text-slate-400">Name</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-slate-400">Description</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-slate-400 hover:text-white"
                onClick={() => setEditing(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                disabled={update.isPending || !editName.trim()}
                onClick={() =>
                  update.mutate({
                    id: editing.id,
                    body: { name: editName.trim(), description: editDesc.trim() || undefined },
                  })
                }
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
            <h2 className="text-lg font-semibold">Delete client?</h2>
            <p className="mt-2 text-sm text-slate-400">
              This removes <span className="font-medium text-slate-200">{deleteTarget.name}</span> and related credentials
              and scans (cascade). This cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-slate-400 hover:text-white"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
                disabled={remove.isPending}
                onClick={() => {
                  remove.mutate(deleteTarget.id, {
                    onSuccess: () => setDeleteTarget(null),
                  });
                }}
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
