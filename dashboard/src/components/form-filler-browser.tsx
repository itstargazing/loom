"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState, Section } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import type {
  DocumentMatch,
  FormDocument,
  FormProfile,
} from "@/lib/types";

const SUGGESTED_KEYS = [
  "full_name",
  "first_name",
  "last_name",
  "email",
  "phone",
  "address_line1",
  "address_line2",
  "city",
  "state",
  "postal_code",
  "country",
  "date_of_birth",
  "company",
  "title",
] as const;

async function readError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  const detail = body && typeof body === "object" ? (body as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: unknown }).msg);
      }
      return String(item);
    });
    if (parts.length) return parts.join("; ");
  }
  return `Request failed (${response.status})`;
}

async function proxyJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

function valuesFromProfile(profile: FormProfile): Array<{ key: string; value: string }> {
  const entries = Object.entries(profile.values).map(([key, value]) => ({
    key,
    value: value == null ? "" : String(value),
  }));
  if (entries.length === 0) return [{ key: "full_name", value: "" }];
  return entries;
}

export function FormFillerBrowser({
  initialProfiles,
  initialDocuments,
}: {
  initialProfiles: FormProfile[];
  initialDocuments: FormDocument[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [profiles, setProfiles] = useState(initialProfiles);
  const [documents, setDocuments] = useState(initialDocuments);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const [profileName, setProfileName] = useState("Personal");
  const [profileRows, setProfileRows] = useState<Array<{ key: string; value: string }>>([
    { key: "full_name", value: "" },
    { key: "email", value: "" },
    { key: "phone", value: "" },
  ]);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [selectedProfileId, setSelectedProfileId] = useState(
    initialProfiles[0]?.id ?? "",
  );
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [matches, setMatches] = useState<DocumentMatch[]>([]);
  const [overrides, setOverrides] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    setProfiles(initialProfiles);
    setDocuments(initialDocuments);
  }, [initialProfiles, initialDocuments]);

  useEffect(() => {
    if (!selectedProfileId && profiles[0]) {
      setSelectedProfileId(profiles[0].id);
    }
  }, [profiles, selectedProfileId]);

  const selectedDocs = useMemo(
    () => documents.filter((doc) => selectedDocIds.includes(doc.id)),
    [documents, selectedDocIds],
  );

  function refresh() {
    startTransition(() => router.refresh());
  }

  function setRow(index: number, patch: Partial<{ key: string; value: string }>) {
    setProfileRows((rows) =>
      rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)),
    );
  }

  function rowsToValues(rows: Array<{ key: string; value: string }>) {
    const values: Record<string, string> = {};
    for (const row of rows) {
      const key = row.key.trim();
      if (!key) continue;
      values[key] = row.value;
    }
    return values;
  }

  async function saveProfile() {
    setError(null);
    const name = profileName.trim();
    if (!name) {
      setError("Profile name cannot be empty");
      return;
    }
    try {
      const values = rowsToValues(profileRows);
      if (editingId) {
        const updated = await proxyJson<FormProfile>(
          `/skills/form-filler/profiles/${editingId}`,
          { method: "PATCH", body: JSON.stringify({ name, values }) },
        );
        setProfiles((current) =>
          current.map((row) => (row.id === updated.id ? updated : row)),
        );
      } else {
        const created = await proxyJson<FormProfile>("/skills/form-filler/profiles", {
          method: "POST",
          body: JSON.stringify({ name, values }),
        });
        setProfiles((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
        setSelectedProfileId(created.id);
      }
      setEditingId(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save profile");
    }
  }

  function startEdit(profile: FormProfile) {
    setEditingId(profile.id);
    setProfileName(profile.name);
    setProfileRows(valuesFromProfile(profile));
  }

  async function removeProfile(profile: FormProfile) {
    if (!window.confirm(`Delete profile ${profile.name}?`)) return;
    setError(null);
    try {
      await proxyJson(`/skills/form-filler/profiles/${profile.id}`, { method: "DELETE" });
      setProfiles((current) => current.filter((row) => row.id !== profile.id));
      if (selectedProfileId === profile.id) setSelectedProfileId("");
      if (editingId === profile.id) setEditingId(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete profile");
    }
  }

  async function uploadFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setError(null);
    setUploading(true);
    const emptyFieldNames: string[] = [];
    try {
      for (const file of Array.from(fileList)) {
        if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
          throw new Error(`${file.name} is not a PDF`);
        }
        const form = new FormData();
        form.append("file", file, file.name);
        const response = await fetch("/api/proxy/skills/form-filler/documents", {
          method: "POST",
          body: form,
        });
        if (!response.ok) throw new Error(await readError(response));
        const created = (await response.json()) as FormDocument;
        if (created.fieldCount === 0) emptyFieldNames.push(created.filename);
        setDocuments((current) => [created, ...current.filter((row) => row.id !== created.id)]);
        setSelectedDocIds((current) =>
          current.includes(created.id) ? current : [...current, created.id],
        );
      }
      setMatches([]);
      if (emptyFieldNames.length) {
        setError(
          `${emptyFieldNames.join(", ")} ${emptyFieldNames.length === 1 ? "has" : "have"} no fillable fields. Stored for Auto-Attach, but Form Filler cannot map profile values onto ${emptyFieldNames.length === 1 ? "it" : "them"}.`,
        );
      }
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not upload PDF");
    } finally {
      setUploading(false);
    }
  }

  async function removeDocument(document: FormDocument) {
    if (!window.confirm(`Remove ${document.filename}?`)) return;
    setError(null);
    try {
      await proxyJson(`/skills/form-filler/documents/${document.id}`, { method: "DELETE" });
      setDocuments((current) => current.filter((row) => row.id !== document.id));
      setSelectedDocIds((current) => current.filter((id) => id !== document.id));
      setMatches((current) => current.filter((row) => row.documentId !== document.id));
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete document");
    }
  }

  function toggleDocument(id: string) {
    setSelectedDocIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  async function runMatch() {
    setError(null);
    if (!selectedProfileId) {
      setError("Select a profile first");
      return;
    }
    if (selectedDocIds.length === 0) {
      setError("Select at least one PDF");
      return;
    }
    try {
      const preview = await proxyJson<DocumentMatch[]>("/skills/form-filler/match", {
        method: "POST",
        body: JSON.stringify({
          profileId: selectedProfileId,
          documentIds: selectedDocIds,
        }),
      });
      setMatches(preview);
      const next: Record<string, Record<string, string>> = {};
      for (const document of preview) {
        next[document.documentId] = {};
        for (const match of document.matches) {
          if (match.needsManual) next[document.documentId][match.fieldName] = "";
        }
      }
      setOverrides(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not match fields");
    }
  }

  function setOverride(documentId: string, fieldName: string, value: string) {
    setOverrides((current) => ({
      ...current,
      [documentId]: { ...(current[documentId] ?? {}), [fieldName]: value },
    }));
  }

  async function downloadZip() {
    setError(null);
    if (!selectedProfileId || selectedDocIds.length === 0) {
      setError("Select a profile and at least one PDF");
      return;
    }
    try {
      const response = await fetch("/api/proxy/skills/form-filler/fill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profileId: selectedProfileId,
          documentIds: selectedDocIds,
          documents: selectedDocIds.map((documentId) => ({
            documentId,
            overrides: Object.entries(overrides[documentId] ?? {})
              .filter(([, value]) => value.trim() !== "")
              .map(([fieldName, value]) => ({ fieldName, value })),
          })),
        }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] ??
        "filled-forms.zip";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not fill forms");
    }
  }

  return (
    <div className="flex flex-col gap-xl">
      {error ? <p className="text-sm text-error">{error}</p> : null}

      <Section title="Profiles">
        <div className="grid gap-lg lg:grid-cols-2">
          <div className="flex flex-col gap-md">
            <label className="flex flex-col gap-1 text-xs text-text-secondary">
              Profile name
              <input
                className="loom-input"
                value={profileName}
                onChange={(event) => setProfileName(event.target.value)}
              />
            </label>
            <div className="flex flex-col gap-sm">
              {profileRows.map((row, index) => (
                <div key={`${index}-${row.key}`} className="grid grid-cols-[10rem_1fr_auto] gap-sm">
                  <input
                    className="loom-input"
                    list="form-profile-keys"
                    value={row.key}
                    placeholder="field"
                    onChange={(event) => setRow(index, { key: event.target.value })}
                  />
                  <input
                    className="loom-input"
                    value={row.value}
                    placeholder="value"
                    onChange={(event) => setRow(index, { value: event.target.value })}
                  />
                  <button
                    type="button"
                    className="text-xs underline"
                    onClick={() =>
                      setProfileRows((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            <datalist id="form-profile-keys">
              {SUGGESTED_KEYS.map((key) => (
                <option key={key} value={key} />
              ))}
            </datalist>
            <div className="flex flex-wrap gap-sm">
              <button
                type="button"
                className="loom-btn loom-btn-secondary"
                onClick={() => setProfileRows((rows) => [...rows, { key: "", value: "" }])}
              >
                Add field
              </button>
              <button type="button" className="loom-btn" disabled={pending} onClick={() => void saveProfile()}>
                {editingId ? "Save profile" : "Create profile"}
              </button>
              {editingId ? (
                <button
                  type="button"
                  className="loom-btn loom-btn-secondary"
                  onClick={() => {
                    setEditingId(null);
                    setProfileName("Personal");
                    setProfileRows([
                      { key: "full_name", value: "" },
                      { key: "email", value: "" },
                      { key: "phone", value: "" },
                    ]);
                  }}
                >
                  Cancel edit
                </button>
              ) : null}
            </div>
          </div>

          <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
            {profiles.length === 0 ? (
              <li className="py-md">
                <EmptyState>No profiles yet. Create one with the values you type on every form.</EmptyState>
              </li>
            ) : (
              profiles.map((profile) => (
                <li key={profile.id} className="flex items-start justify-between gap-md py-md">
                  <div>
                    <p className="text-sm font-medium">{profile.name}</p>
                    <p className="mt-1 text-xs text-text-secondary">
                      {Object.keys(profile.values).length} values
                      {" · "}
                      <RelativeTime iso={profile.updatedAt} />
                    </p>
                  </div>
                  <div className="flex gap-sm">
                    <button type="button" className="text-xs underline" onClick={() => startEdit(profile)}>
                      Edit
                    </button>
                    <button type="button" className="text-xs underline" onClick={() => void removeProfile(profile)}>
                      Delete
                    </button>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      </Section>

      <Section title="Documents">
        <div className="flex flex-col gap-sm">
          <label className="loom-btn loom-btn-secondary w-fit cursor-pointer">
            {uploading ? "Uploading…" : "Upload PDF"}
            <input
              className="sr-only"
              type="file"
              accept="application/pdf,.pdf"
              multiple
              disabled={uploading}
              onChange={(event) => {
                void uploadFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </label>
          <p className="text-xs text-text-secondary">
            Standard fillable PDFs (AcroForm) can be matched to a profile. Scanned or flattened
            PDFs still upload; they just will not auto-fill.
          </p>
        </div>
        {documents.length === 0 ? (
          <EmptyState>
            Upload PDFs here, or open a fillable PDF in the LOOM viewer and choose Add to Form
            Filler. File bytes go over HTTP, not the extension message bus.
          </EmptyState>
        ) : (
          <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
            {documents.map((document) => (
              <li key={document.id} className="flex items-start justify-between gap-md py-md">
                <label className="flex min-w-0 items-start gap-sm text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedDocIds.includes(document.id)}
                    onChange={() => toggleDocument(document.id)}
                  />
                  <span>
                    <span className="font-medium">{document.filename}</span>
                    <span className="mt-1 block text-xs text-text-secondary">
                      {document.fieldCount === 0
                        ? "No fillable fields"
                        : `${document.fieldCount} fields`}
                      {document.sourceUrl ? ` · ${document.sourceUrl}` : ""}
                      {" · "}
                      <RelativeTime iso={document.createdAt} />
                    </span>
                  </span>
                </label>
                <button
                  type="button"
                  className="text-xs underline"
                  onClick={() => void removeDocument(document)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Match and fill">
        <div className="flex flex-wrap items-end gap-md">
          <label className="flex min-w-48 flex-col gap-1 text-xs text-text-secondary">
            Profile
            <select
              className="loom-input"
              value={selectedProfileId}
              onChange={(event) => setSelectedProfileId(event.target.value)}
            >
              <option value="">Select…</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="loom-btn" disabled={pending} onClick={() => void runMatch()}>
            Preview matches
          </button>
          <button
            type="button"
            className="loom-btn loom-btn-secondary"
            disabled={pending}
            onClick={() => void downloadZip()}
          >
            Fill and download zip
          </button>
        </div>
        <p className="text-xs text-text-secondary">
          {selectedDocs.length} PDF{selectedDocs.length === 1 ? "" : "s"} selected. Low-confidence
          fields stay blank until you type an override.
        </p>

        {matches.length === 0 ? (
          <EmptyState>
            Choose a profile and PDFs, then preview matches before downloading filled copies.
          </EmptyState>
        ) : (
          <div className="flex flex-col gap-lg">
            {matches.map((document) => (
              <div key={document.documentId} className="loom-card flex flex-col gap-sm p-md">
                <div className="flex items-baseline justify-between gap-md">
                  <h3 className="text-sm font-medium">{document.filename}</h3>
                  <p className="text-xs text-text-secondary">
                    {document.autoFilled} filled · {document.needsManual} need review
                  </p>
                </div>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="font-mono text-xs text-text-secondary">
                      <th className="py-1 pr-md font-medium">Field</th>
                      <th className="py-1 pr-md font-medium">Value</th>
                      <th className="py-1 font-medium">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {document.matches.map((match) => (
                      <tr key={match.fieldName} className="border-t border-border">
                        <td className="py-2 pr-md align-top">
                          <span className="loom-mono text-xs">{match.fieldName}</span>
                          {match.needsManual ? (
                            <span className="mt-1 block text-xs text-warning">Left blank</span>
                          ) : null}
                        </td>
                        <td className="py-2 pr-md">
                          {match.needsManual ? (
                            <input
                              className="loom-input"
                              value={overrides[document.documentId]?.[match.fieldName] ?? ""}
                              placeholder={match.reason}
                              onChange={(event) =>
                                setOverride(document.documentId, match.fieldName, event.target.value)
                              }
                            />
                          ) : (
                            <span>{match.value}</span>
                          )}
                        </td>
                        <td className="py-2 align-top text-xs text-text-secondary">
                          {Math.round(match.confidence * 100)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
