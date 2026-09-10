"use client";

import { emptyExamOrder, type ExamOrders } from "@/contracts/consultation";
import type { DocumentHeader } from "@/contracts/documentHeader";
import { messages } from "@/i18n/pt-BR";

import { DocumentHeaderFields } from "./DocumentHeaderFields";
import { DocumentPaper, printDocument } from "./DocumentPaper";
import { InlineEdit } from "./InlineEdit";

type ExamOrdersDraftProps = {
  examOrders: ExamOrders;
  header: DocumentHeader;
  onChange: (examOrders: ExamOrders) => void;
  onHeaderChange: (header: DocumentHeader) => void;
};

export function ExamOrdersDraft({
  examOrders,
  header,
  onChange,
  onHeaderChange,
}: ExamOrdersDraftProps) {
  function updateExam(
    index: number,
    field: keyof ExamOrders["exams"][number],
    value: string,
  ): void {
    onChange({
      exams: examOrders.exams.map((exam, current) =>
        current === index ? { ...exam, [field]: value } : exam,
      ),
    });
  }

  return (
    <DocumentPaper
      printId="exam_orders"
      onPrint={() => {
        printDocument("exam_orders");
      }}
    >
      <header className="paper-heading">
        <p className="paper-kicker">{messages.appName}</p>
        <h2>{messages.examOrdersTitle}</h2>
      </header>
      <DocumentHeaderFields header={header} onChange={onHeaderChange} />
      {examOrders.exams.length === 0 ? (
        <p className="empty-hint">{messages.noExams}</p>
      ) : (
        <ol className="exam-list">
          {examOrders.exams.map((exam, index) => (
            <li key={`exam-${index}`}>
              <InlineEdit
                value={exam.name}
                onChange={(value) => {
                  updateExam(index, "name", value);
                }}
                aria-label={`${messages.examName} ${index + 1}`}
                className="is-strong"
              />
              <p>
                <span>{messages.indication}: </span>
                <InlineEdit
                  value={exam.indication}
                  multiline
                  onChange={(value) => {
                    updateExam(index, "indication", value);
                  }}
                  aria-label={messages.indication}
                />
              </p>
              <p>
                <span>{messages.prep}: </span>
                <InlineEdit
                  value={exam.instructions}
                  multiline
                  onChange={(value) => {
                    updateExam(index, "instructions", value);
                  }}
                  aria-label={messages.prep}
                />
              </p>
              <button
                type="button"
                className="text-button no-print"
                onClick={() => {
                  onChange({
                    exams: examOrders.exams.filter(
                      (_, current) => current !== index,
                    ),
                  });
                }}
              >
                {messages.removeExam}
              </button>
            </li>
          ))}
        </ol>
      )}
      <button
        type="button"
        className="text-button no-print"
        onClick={() => {
          onChange({ exams: [...examOrders.exams, emptyExamOrder()] });
        }}
      >
        {messages.addExam}
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
