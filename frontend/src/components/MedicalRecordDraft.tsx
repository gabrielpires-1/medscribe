"use client";

import type { SoapNote } from "@/contracts/consultation";
import type { DocumentHeader } from "@/contracts/documentHeader";
import { messages } from "@/i18n/pt-BR";

import { DocumentHeaderFields } from "./DocumentHeaderFields";
import { DocumentPaper, printDocument } from "./DocumentPaper";
import { InlineEdit } from "./InlineEdit";

type MedicalRecordDraftProps = {
  medicalRecord: SoapNote;
  header: DocumentHeader;
  onChange: (medicalRecord: SoapNote) => void;
  onHeaderChange: (header: DocumentHeader) => void;
};

const SOAP_SECTIONS: {
  field: keyof SoapNote;
  label: string;
  accent: string;
}[] = [
  { field: "subjective", label: messages.subjective, accent: "is-s" },
  { field: "objective", label: messages.objective, accent: "is-o" },
  { field: "assessment", label: messages.assessment, accent: "is-a" },
  { field: "plan", label: messages.plan, accent: "is-p" },
];

export function MedicalRecordDraft({
  medicalRecord,
  header,
  onChange,
  onHeaderChange,
}: MedicalRecordDraftProps) {
  return (
    <DocumentPaper
      printId="medical_record"
      onPrint={() => {
        printDocument("medical_record");
      }}
    >
      <header className="paper-heading">
        <p className="paper-kicker">{messages.appName}</p>
        <h2>{messages.medicalRecordTitle}</h2>
      </header>
      <DocumentHeaderFields header={header} onChange={onHeaderChange} />
      {SOAP_SECTIONS.map((section) => (
        <section
          key={section.field}
          className={`soap-block ${section.accent}`}
        >
          <h3>{section.label}</h3>
          <InlineEdit
            value={medicalRecord[section.field]}
            multiline
            onChange={(value) => {
              onChange({ ...medicalRecord, [section.field]: value });
            }}
            aria-label={section.label}
          />
        </section>
      ))}
      <footer className="paper-footer">
        <div className="signature-line">
          <span />
          <p>
            {header.doctorName || messages.doctor}
            <br />
            {messages.crm} {header.crm || "—"}
          </p>
        </div>
      </footer>
    </DocumentPaper>
  );
}
