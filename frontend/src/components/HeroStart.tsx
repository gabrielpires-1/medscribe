"use client";

import { useRef } from "react";

import { flags } from "@/flags";
import { messages } from "@/i18n/pt-BR";

type HeroStartProps = {
  disabled?: boolean;
  onStart: () => void;
  onReadyAudio: (file: File) => void;
};

export function HeroStart({
  disabled = false,
  onStart,
  onReadyAudio,
}: HeroStartProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <section className="hero no-print" aria-label={messages.record}>
      <button
        type="button"
        className="hero-mic"
        onClick={onStart}
        disabled={disabled}
        aria-label={messages.record}
      >
        <span className="hero-mic-glow" aria-hidden="true" />
        <MicIcon size={34} />
      </button>

      <div className="hero-copy">
        <h1>{messages.heroTitle}</h1>
        <p>{messages.heroSubtitle}</p>
      </div>

      <div className="hero-actions">
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={onStart}
          disabled={disabled}
        >
          <MicIcon size={20} />
          {messages.record}
        </button>

        {flags.readyAudioUpload ? (
          <>
            <span className="hero-or">{messages.heroOrUpload}</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.wav,.mp3,.webm,.m4a,.ogg"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file && file.size > 0) {
                  onReadyAudio(file);
                }
              }}
            />
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                fileInputRef.current?.click();
              }}
              disabled={disabled}
            >
              {messages.sendReadyAudio}
            </button>
          </>
        ) : null}
      </div>

      <ol className="hero-tips">
        <li>
          <span className="hero-tip-title">{messages.heroTip1Title}</span>
          <span className="hero-tip-body">{messages.heroTip1Body}</span>
        </li>
        <li>
          <span className="hero-tip-title">{messages.heroTip2Title}</span>
          <span className="hero-tip-body">{messages.heroTip2Body}</span>
        </li>
        <li>
          <span className="hero-tip-title">{messages.heroTip3Title}</span>
          <span className="hero-tip-body">{messages.heroTip3Body}</span>
        </li>
      </ol>
    </section>
  );
}

function MicIcon({ size = 24 }: { size?: number }) {
  return (
    <svg
      className="mic-icon"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V20H8v2h8v-2h-3v-2.08A7 7 0 0 0 19 11h-2Z"
      />
    </svg>
  );
}
