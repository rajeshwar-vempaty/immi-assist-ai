"use client";

import { useEffect, useState } from "react";
import { getCaseProfile, updateCaseProfile } from "../lib/api";

const VISA_OPTIONS = [
  "",
  "H1B",
  "H4",
  "L1A",
  "L1B",
  "O1",
  "EB1",
  "EB2",
  "EB2_NIW",
  "EB3",
  "F1",
  "F1_OPT",
  "I-485",
  "I-140",
  "OTHER",
];

const empty = {
  visa_type: "",
  form_number: "",
  service_center: "",
  office_code: "",
  priority_date: "",
  country_of_chargeability: "",
  has_dependents: false,
  premium_processing: false,
  employer_name: "",
  notes: "",
};

export default function CaseProfilePanel({ onChange, compact = false }) {
  const [open, setOpen] = useState(!compact);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getCaseProfile()
      .then((data) => {
        if (cancelled) return;
        const next = { ...empty, ...data };
        setForm(next);
        onChange?.(next);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // Load once on mount; parent can still receive updates via Save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    setSaving(true);
    setError("");
    setStatus("");
    try {
      const saved = await updateCaseProfile({
        visa_type: form.visa_type || null,
        form_number: form.form_number || null,
        service_center: form.service_center || null,
        office_code: form.office_code || null,
        priority_date: form.priority_date || null,
        country_of_chargeability: form.country_of_chargeability || null,
        has_dependents: !!form.has_dependents,
        premium_processing: !!form.premium_processing,
        employer_name: form.employer_name || null,
        notes: form.notes || "",
      });
      const next = { ...empty, ...saved };
      setForm(next);
      onChange?.(next);
      setStatus("Saved");
    } catch (err) {
      setError(err.message || "Could not save case profile");
    } finally {
      setSaving(false);
    }
  };

  const summary = [
    form.visa_type,
    form.form_number,
    form.service_center || form.office_code,
    form.priority_date ? `PD ${form.priority_date}` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className={`case-profile ${open ? "open" : ""}`}>
      <button
        type="button"
        className="case-profile-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>
          <strong>Case profile</strong>
          <span className="case-profile-summary">
            {summary || "Add visa, form, office, priority date — reused across tabs"}
          </span>
        </span>
        <span className="case-profile-chevron">{open ? "Hide" : "Edit"}</span>
      </button>
      {open && (
        <div className="case-profile-body">
          <div className="case-profile-grid">
            <label>
              Visa / petition
              <select
                className="select"
                value={form.visa_type || ""}
                onChange={(e) => setField("visa_type", e.target.value)}
              >
                {VISA_OPTIONS.map((v) => (
                  <option key={v || "blank"} value={v}>
                    {v || "Select…"}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Primary form
              <input
                className="input"
                value={form.form_number || ""}
                onChange={(e) => setField("form_number", e.target.value)}
                placeholder="e.g. I-129"
              />
            </label>
            <label>
              Service center / office
              <input
                className="input"
                value={form.service_center || ""}
                onChange={(e) => setField("service_center", e.target.value)}
                placeholder="e.g. California Service Center"
              />
            </label>
            <label>
              Priority date
              <input
                className="input"
                value={form.priority_date || ""}
                onChange={(e) => setField("priority_date", e.target.value)}
                placeholder="YYYY-MM-DD"
              />
            </label>
            <label>
              Country of chargeability
              <input
                className="input"
                value={form.country_of_chargeability || ""}
                onChange={(e) => setField("country_of_chargeability", e.target.value)}
                placeholder="e.g. India"
              />
            </label>
            <label>
              Employer
              <input
                className="input"
                value={form.employer_name || ""}
                onChange={(e) => setField("employer_name", e.target.value)}
                placeholder="Employer name"
              />
            </label>
          </div>
          <div className="case-profile-checks">
            <label className="check">
              <input
                type="checkbox"
                checked={!!form.has_dependents}
                onChange={(e) => setField("has_dependents", e.target.checked)}
              />
              Has dependents
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!form.premium_processing}
                onChange={(e) => setField("premium_processing", e.target.checked)}
              />
              Premium processing
            </label>
          </div>
          <label className="case-profile-notes">
            Notes
            <textarea
              className="field"
              rows={2}
              value={form.notes || ""}
              onChange={(e) => setField("notes", e.target.value)}
              placeholder="Anything Checklist / RFE / Chat should know…"
            />
          </label>
          <div className="case-profile-actions">
            <button type="button" className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save profile"}
            </button>
            {status ? <span className="case-profile-status">{status}</span> : null}
            {error ? <span className="case-profile-error">{error}</span> : null}
          </div>
        </div>
      )}
    </section>
  );
}
