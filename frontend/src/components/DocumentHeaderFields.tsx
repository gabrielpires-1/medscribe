"use client";

import type { DocumentHeader } from "@/contracts/documentHeader";
import { messages } from "@/i18n/pt-BR";

import { InlineEdit } from "./InlineEdit";

type DocumentHeaderFieldsProps = {
  header: DocumentHeader;
  onChange: (header: DocumentHeader) => void;
};

export function DocumentHeaderFields({
  header,
  onChange,
}: DocumentHeaderFieldsProps) {
  function update<K extends keyof DocumentHeader>(
    field: K,
    value: DocumentHeader[K],
  ): void {
    onChange({ ...header, [field]: value });
  }

  return (
    <dl className="doc-header">
      <div>
        <dt>{messages.patient}</dt>
        <dd>
          <InlineEdit
            value={header.patientName}
            onChange={(value) => {
              update("patientName", value);
            }}
            aria-label={messages.patient}
          />
        </dd>
      </div>
      <div>
        <dt>{messages.doctor}</dt>
        <dd>
          <InlineEdit
            value={header.doctorName}
            onChange={(value) => {
              update("doctorName", value);
            }}
            aria-label={messages.doctor}
          />
        </dd>
      </div>
      <div>
        <dt>{messages.crm}</dt>
        <dd>
          <InlineEdit
            value={header.crm}
            onChange={(value) => {
              update("crm", value);
            }}
            aria-label={messages.crm}
          />
        </dd>
      </div>
      <div>
        <dt>{messages.city}</dt>
        <dd>
          <InlineEdit
            value={header.city}
            onChange={(value) => {
              update("city", value);
            }}
            aria-label={messages.city}
          />
        </dd>
      </div>
      <div>
        <dt>{messages.date}</dt>
        <dd>
          <InlineEdit
            value={header.date}
            onChange={(value) => {
              update("date", value);
            }}
            aria-label={messages.date}
          />
        </dd>
      </div>
    </dl>
  );
}
