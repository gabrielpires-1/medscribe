"use client";

import { useState } from "react";

import { messages } from "@/i18n/pt-BR";

type InlineEditProps = {
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
};

export function InlineEdit({
  value,
  onChange,
  multiline = false,
  placeholder = messages.emptyPlaceholder,
  className,
  "aria-label": ariaLabel,
}: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  function beginEdit(): void {
    setDraft(value);
    setEditing(true);
  }

  function commit(): void {
    onChange(draft);
    setEditing(false);
  }

  function cancel(): void {
    setDraft(value);
    setEditing(false);
  }

  if (!editing) {
    return (
      <span
        className={`inline-edit ${value ? "" : "is-empty"} ${className ?? ""}`}
        onClick={beginEdit}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            beginEdit();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label={ariaLabel}
      >
        {value || placeholder}
      </span>
    );
  }

  if (multiline) {
    return (
      <textarea
        className={`inline-edit-input is-multiline ${className ?? ""}`}
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
        }}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            cancel();
          }
        }}
        aria-label={ariaLabel}
        autoFocus
        rows={4}
      />
    );
  }

  return (
    <input
      className={`inline-edit-input ${className ?? ""}`}
      value={draft}
      onChange={(event) => {
        setDraft(event.target.value);
      }}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          commit();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          cancel();
        }
      }}
      aria-label={ariaLabel}
      autoFocus
    />
  );
}
