"use client";

import type { ReactNode } from "react";

import { messages } from "@/i18n/pt-BR";

type DocumentPaperProps = {
  printId: string;
  children: ReactNode;
  onPrint: () => void;
};

export function DocumentPaper({
  printId,
  children,
  onPrint,
}: DocumentPaperProps) {
  return (
    <article className="document-card" data-print-id={printId}>
      <div className="document-toolbar no-print">
        <span className="draft-badge">{messages.draftBadge}</span>
        <button type="button" className="print-button" onClick={onPrint}>
          {messages.print}
        </button>
      </div>
      <div className="document-paper">{children}</div>
    </article>
  );
}

export function printDocument(printId: string): void {
  document.body.dataset.print = printId;
  const cleanup = () => {
    delete document.body.dataset.print;
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);
  window.print();
}
