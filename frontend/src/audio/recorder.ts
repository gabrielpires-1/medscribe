import { messages } from "@/i18n/pt-BR";

export class MicrophonePermissionError extends Error {
  constructor() {
    super(messages.micDenied);
    this.name = "MicrophonePermissionError";
  }
}

export function pickAudioMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "audio/webm";
  }
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? "";
}

export class ConsultationRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private stream: MediaStream | null = null;

  async start(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      throw new MicrophonePermissionError();
    }
    this.chunks = [];
    const mimeType = pickAudioMimeType();
    this.mediaRecorder = mimeType
      ? new MediaRecorder(this.stream, { mimeType })
      : new MediaRecorder(this.stream);
    this.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data);
      }
    });
    this.mediaRecorder.start();
  }

  async stop(): Promise<Blob> {
    const recorder = this.mediaRecorder;
    if (!recorder) {
      throw new Error(messages.uploadError);
    }
    return new Promise((resolve, reject) => {
      recorder.addEventListener(
        "stop",
        () => {
          const type = recorder.mimeType || "audio/webm";
          const blob = new Blob(this.chunks, { type });
          this.cleanup();
          if (blob.size === 0) {
            reject(new Error(messages.uploadError));
            return;
          }
          resolve(blob);
        },
        { once: true },
      );
      recorder.stop();
    });
  }

  private cleanup(): void {
    this.stream?.getTracks().forEach((track) => {
      track.stop();
    });
    this.stream = null;
    this.mediaRecorder = null;
    this.chunks = [];
  }
}

export function downloadRecording(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function localRecordingName(recordingId: string, filename?: string): string {
  const source =
    filename && filename.includes(".") ? filename : "consulta.webm";
  const ext = source.slice(source.lastIndexOf("."));
  return `${recordingId}${ext}`;
}

export async function saveRecordingLocally(
  blob: Blob,
  recordingId: string,
  filename?: string,
): Promise<boolean> {
  const form = new FormData();
  form.append("file", blob, localRecordingName(recordingId, filename));
  form.append("id", recordingId);
  try {
    const response = await fetch("/api/recordings", {
      method: "POST",
      body: form,
    });
    return response.ok;
  } catch {
    return false;
  }
}
