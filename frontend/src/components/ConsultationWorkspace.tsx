"use client";

import { useEffect, useRef, useState } from "react";

import {
  ConsultationApiError,
  isAbortError,
  createConsultation,
  pollConsultation,
  retryExtract,
} from "@/api/consultations";
import {
  ConsultationRecorder,
  MicrophonePermissionError,
  downloadRecording,
  saveRecordingLocally,
} from "@/audio/recorder";
import type { ConsultationDocuments } from "@/contracts/consultation";
import {
  emptyDocumentHeader,
  type DocumentHeader,
} from "@/contracts/documentHeader";
import { messages } from "@/i18n/pt-BR";

import { ExamOrdersDraft } from "./ExamOrdersDraft";
import { HeroStart } from "./HeroStart";
import { MedicalRecordDraft } from "./MedicalRecordDraft";
import { PipelineLoader } from "./PipelineLoader";
import { PrescriptionDraft } from "./PrescriptionDraft";
import { RecordingPanel } from "./RecordingPanel";

type Phase = "idle" | "recording" | "processing" | "ready" | "failed";

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function recordingFilename(id: string, filename?: string): string {
  const source = filename && filename.includes(".") ? filename : "consulta.webm";
  const ext = source.slice(source.lastIndexOf("."));
  return `${id}${ext}`;
}

async function persistRecording(
  blob: Blob,
  id: string,
  filename?: string,
): Promise<void> {
  const saved = await saveRecordingLocally(blob, id, filename);
  if (!saved) {
    downloadRecording(blob, recordingFilename(id, filename));
  }
}

export function ConsultationWorkspace() {
  const recorderRef = useRef<ConsultationRecorder | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [consultationId, setConsultationId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<ConsultationDocuments | null>(
    null,
  );
  const [header, setHeader] = useState<DocumentHeader>(emptyDocumentHeader);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (phase !== "recording") {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [phase]);

  useEffect(() => {
    if (phase !== "processing" || !consultationId) {
      return undefined;
    }
    const controller = new AbortController();
    void (async () => {
      try {
        const result = await pollConsultation(consultationId, controller.signal);
        if (result.status === "succeeded" && result.documents) {
          setDocuments(result.documents);
          setErrorMessage(null);
          setPhase("ready");
          return;
        }
        setErrorMessage(result.error ?? messages.failedTitle);
        setPhase("failed");
      } catch (error) {
        if (isAbortError(error)) {
          return;
        }
        setErrorMessage(
          error instanceof ConsultationApiError
            ? error.message
            : messages.uploadError,
        );
        setPhase("failed");
      }
    })();
    return () => {
      controller.abort();
    };
  }, [phase, consultationId]);

  async function handleStart(): Promise<void> {
    setErrorMessage(null);
    const recorder = new ConsultationRecorder();
    try {
      await recorder.start();
    } catch (error) {
      setErrorMessage(
        error instanceof MicrophonePermissionError
          ? error.message
          : messages.micDenied,
      );
      return;
    }
    recorderRef.current = recorder;
    setElapsedSeconds(0);
    setDocuments(null);
    setConsultationId(null);
    setPhase("recording");
  }

  async function handleStop(): Promise<void> {
    const recorder = recorderRef.current;
    if (!recorder) {
      return;
    }
    recorderRef.current = null;
    let blob: Blob;
    try {
      blob = await recorder.stop();
    } catch {
      setErrorMessage(messages.uploadError);
      setPhase("idle");
      return;
    }
    await submitAudio(blob);
  }

  async function handleReadyAudio(file: File): Promise<void> {
    setErrorMessage(null);
    setDocuments(null);
    setConsultationId(null);
    await submitAudio(file, file.name);
  }

  async function submitAudio(blob: Blob, filename?: string): Promise<void> {
    setPhase("processing");
    const fallbackId = `rec-${new Date().toISOString().replace(/[:.]/g, "-")}`;
    try {
      const accepted = await createConsultation(blob, filename);
      setConsultationId(accepted.id);
      await persistRecording(blob, accepted.id, filename);
    } catch (error) {
      await persistRecording(blob, fallbackId, filename);
      setErrorMessage(
        error instanceof ConsultationApiError
          ? error.message
          : messages.uploadError,
      );
      setPhase("failed");
    }
  }

  async function handleRetryExtract(): Promise<void> {
    if (!consultationId) {
      return;
    }
    setErrorMessage(null);
    try {
      await retryExtract(consultationId);
      setPhase("processing");
    } catch (error) {
      if (error instanceof ConsultationApiError && error.status === 409) {
        setErrorMessage(messages.extractNotReady);
        setPhase("failed");
        return;
      }
      setErrorMessage(
        error instanceof ConsultationApiError
          ? error.message
          : messages.uploadError,
      );
      setPhase("failed");
    }
  }

  return (
    <div className="workspace">
      <header className="app-header no-print">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22">
              <path
                fill="currentColor"
                d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V20H8v2h8v-2h-3v-2.08A7 7 0 0 0 19 11h-2Z"
              />
            </svg>
          </span>
          <span className="brand-text">
            <span className="brand-name">{messages.appName}</span>
            <span className="brand-tagline">{messages.appTagline}</span>
          </span>
        </div>

        <span
          className={`header-status${
            phase === "recording" ? " is-recording" : ""
          }`}
          aria-live="polite"
        >
          {phase === "recording" ? (
            <>
              <span className="header-status-dot" aria-hidden="true" />
              {messages.recording}
              <span className="header-status-timer">
                {formatElapsed(elapsedSeconds)}
              </span>
            </>
          ) : (
            <>
              <span className="header-status-idle-dot" aria-hidden="true" />
              {messages.headerStatusIdle}
            </>
          )}
        </span>
      </header>

      {errorMessage && phase !== "processing" ? (
        <div className="banner is-error no-print" role="alert">
          <p>
            <strong>{messages.failedTitle}</strong>
            {errorMessage}
          </p>
          <div className="banner-actions">
            {consultationId ? (
              <button type="button" onClick={() => void handleRetryExtract()}>
                {messages.retryExtract}
              </button>
            ) : null}
            <button type="button" className="is-secondary" onClick={handleStart}>
              {messages.recordAgain}
            </button>
          </div>
        </div>
      ) : null}

      {phase === "idle" || (phase === "failed" && !documents) ? (
        <HeroStart
          disabled={false}
          onStart={() => {
            void handleStart();
          }}
          onReadyAudio={(file) => {
            void handleReadyAudio(file);
          }}
        />
      ) : null}

      {phase === "recording" ? (
        <RecordingPanel
          elapsedSeconds={elapsedSeconds}
          onStop={() => {
            void handleStop();
          }}
        />
      ) : null}

      {phase === "processing" ? <PipelineLoader /> : null}

      {phase === "ready" && documents ? (
        <section className="documents" aria-label={messages.draftBadge}>
          <MedicalRecordDraft
            medicalRecord={documents.medical_record}
            header={header}
            onChange={(medicalRecord) => {
              setDocuments({ ...documents, medical_record: medicalRecord });
            }}
            onHeaderChange={setHeader}
          />
          <PrescriptionDraft
            prescription={documents.prescription}
            header={header}
            onChange={(prescription) => {
              setDocuments({ ...documents, prescription });
            }}
            onHeaderChange={setHeader}
          />
          <ExamOrdersDraft
            examOrders={documents.exam_orders}
            header={header}
            onChange={(examOrders) => {
              setDocuments({ ...documents, exam_orders: examOrders });
            }}
            onHeaderChange={setHeader}
          />
        </section>
      ) : null}
    </div>
  );
}
