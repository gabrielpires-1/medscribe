import type {
  ConsultationAccepted,
  ConsultationRead,
} from "@/contracts/consultation";
import { messages } from "@/i18n/pt-BR";

export const CONSULTATION_POLL_INTERVAL_MS = 2000;

export class ConsultationApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ConsultationApiError";
    this.status = status;
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (
      payload !== null &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }
  } catch {
    return messages.uploadError;
  }
  return messages.uploadError;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ConsultationApiError(
      response.status,
      await readErrorDetail(response),
    );
  }
  return (await response.json()) as T;
}

function consultationFilename(file: Blob, filename?: string): string {
  if (filename && filename.trim() !== "") {
    return filename;
  }
  if (file instanceof File && file.name.trim() !== "") {
    return file.name;
  }
  return "consulta.webm";
}

export async function createConsultation(
  file: Blob,
  filename?: string,
): Promise<ConsultationAccepted> {
  const form = new FormData();
  form.append("file", file, consultationFilename(file, filename));
  const response = await fetch("/consultations", {
    method: "POST",
    body: form,
  });
  return parseJson<ConsultationAccepted>(response);
}

export async function getConsultation(
  consultationId: string,
): Promise<ConsultationRead> {
  const response = await fetch(`/consultations/${consultationId}`);
  return parseJson<ConsultationRead>(response);
}

export async function retryExtract(
  consultationId: string,
): Promise<ConsultationAccepted> {
  const response = await fetch(`/consultations/${consultationId}/extract`, {
    method: "POST",
  });
  return parseJson<ConsultationAccepted>(response);
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function pollConsultation(
  consultationId: string,
  signal?: AbortSignal,
): Promise<ConsultationRead> {
  while (!signal?.aborted) {
    const current = await getConsultation(consultationId);
    if (current.status === "succeeded" || current.status === "failed") {
      return current;
    }
    await sleep(CONSULTATION_POLL_INTERVAL_MS, signal);
  }
  throw new DOMException("Aborted", "AbortError");
}
