"use client";

import { emptyMedication, type Prescription } from "@/contracts/consultation";
import type { DocumentHeader } from "@/contracts/documentHeader";
import { messages } from "@/i18n/pt-BR";

import { DocumentHeaderFields } from "./DocumentHeaderFields";
import { DocumentPaper, printDocument } from "./DocumentPaper";
import { InlineEdit } from "./InlineEdit";

type PrescriptionDraftProps = {
  prescription: Prescription;
  header: DocumentHeader;
  onChange: (prescription: Prescription) => void;
  onHeaderChange: (header: DocumentHeader) => void;
};

export function PrescriptionDraft({
  prescription,
  header,
  onChange,
  onHeaderChange,
}: PrescriptionDraftProps) {
  function updateMedication(
    index: number,
    field: keyof Prescription["medications"][number],
    value: string,
  ): void {
    onChange({
      medications: prescription.medications.map((medication, current) =>
        current === index ? { ...medication, [field]: value } : medication,
      ),
    });
  }

  return (
    <DocumentPaper
      printId="prescription"
      onPrint={() => {
        printDocument("prescription");
      }}
    >
      <header className="paper-heading is-receita">
        <p className="paper-kicker">{messages.appName}</p>
        <h2>{messages.prescriptionTitle}</h2>
        <p className="use-internal">{messages.internalUse}</p>
      </header>
      <DocumentHeaderFields header={header} onChange={onHeaderChange} />
      {prescription.medications.length === 0 ? (
        <p className="empty-hint">{messages.noMedications}</p>
      ) : (
        <ol className="medication-list">
          {prescription.medications.map((medication, index) => (
            <li key={`medication-${index}`}>
              <div className="medication-title">
                <InlineEdit
                  value={medication.name}
                  onChange={(value) => {
                    updateMedication(index, "name", value);
                  }}
                  aria-label={`${messages.medicationName} ${index + 1}`}
                  className="is-strong"
                />
                <InlineEdit
                  value={medication.dosage}
                  onChange={(value) => {
                    updateMedication(index, "dosage", value);
                  }}
                  aria-label={messages.dosage}
                  className="is-strong"
                />
              </div>
              <p className="medication-posology">
                <span>{messages.route}: </span>
                <InlineEdit
                  value={medication.route}
                  onChange={(value) => {
                    updateMedication(index, "route", value);
                  }}
                  aria-label={messages.route}
                />
                <span> · {messages.frequency}: </span>
                <InlineEdit
                  value={medication.frequency}
                  onChange={(value) => {
                    updateMedication(index, "frequency", value);
                  }}
                  aria-label={messages.frequency}
                />
                <span> · {messages.duration}: </span>
                <InlineEdit
                  value={medication.duration}
                  onChange={(value) => {
                    updateMedication(index, "duration", value);
                  }}
                  aria-label={messages.duration}
                />
              </p>
              <p className="medication-instructions">
                <span>{messages.instructions}: </span>
                <InlineEdit
                  value={medication.instructions}
                  multiline
                  onChange={(value) => {
                    updateMedication(index, "instructions", value);
                  }}
                  aria-label={messages.instructions}
                />
              </p>
              <button
                type="button"
                className="text-button no-print"
                onClick={() => {
                  onChange({
                    medications: prescription.medications.filter(
                      (_, current) => current !== index,
                    ),
                  });
                }}
              >
                {messages.removeMedication}
              </button>
            </li>
          ))}
        </ol>
      )}
      <button
        type="button"
        className="text-button no-print"
        onClick={() => {
          onChange({
            medications: [...prescription.medications, emptyMedication()],
          });
        }}
      >
        {messages.addMedication}
      </button>
      <footer className="paper-footer">
        <div className="signature-line">
          <span />
          <p>
            {messages.signature}
            <br />
            {header.doctorName || messages.doctor}
            <br />
            {messages.crm} {header.crm || "—"}
          </p>
        </div>
      </footer>
    </DocumentPaper>
  );
}
