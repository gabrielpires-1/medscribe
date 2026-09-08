"use client";

import { messages } from "@/i18n/pt-BR";

type RecordingPanelProps = {
  elapsedSeconds: number;
  disabled?: boolean;
  onStop: () => void;
};

const WAVEFORM_BARS = 9;

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function RecordingPanel({
  elapsedSeconds,
  disabled = false,
  onStop,
}: RecordingPanelProps) {
  return (
    <section
      className="recording-panel no-print"
      role="status"
      aria-live="polite"
    >
      <p className="recording-badge">
        <span className="recording-dot" aria-hidden="true" />
        {messages.recording}
      </p>

      <div className="recording-visual" aria-hidden="true">
        <span className="recording-ring recording-ring-1" />
        <span className="recording-ring recording-ring-2" />
        <div className="recording-core">
          <svg viewBox="0 0 24 24" width="40" height="40">
            <path
              fill="currentColor"
              d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V20H8v2h8v-2h-3v-2.08A7 7 0 0 0 19 11h-2Z"
            />
          </svg>
        </div>
      </div>

      <p className="recording-timer" aria-label={messages.elapsedLabel}>
        {formatElapsed(elapsedSeconds)}
      </p>

      <div className="waveform" aria-hidden="true">
        {Array.from({ length: WAVEFORM_BARS }).map((_, index) => (
          <span
            key={index}
            className="waveform-bar"
            style={{ animationDelay: `${index * 0.12}s` }}
          />
        ))}
      </div>

      <p className="recording-hint">{messages.recordingSubtitle}</p>

      <button
        type="button"
        className="btn btn-stop btn-lg"
        onClick={onStop}
        disabled={disabled}
      >
        <span className="stop-square" aria-hidden="true" />
        {messages.stopAndSend}
      </button>
    </section>
  );
}
