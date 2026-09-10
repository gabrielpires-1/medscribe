"use client";

import { useEffect, useState } from "react";

import { messages, pipelineStages } from "@/i18n/pt-BR";

const STEP_INTERVAL_MS = 2200;

export function PipelineLoader() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveStep((current) =>
        Math.min(current + 1, pipelineStages.length - 1),
      );
    }, STEP_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const progress = ((activeStep + 1) / pipelineStages.length) * 100;

  return (
    <section
      className="pipeline-loader no-print"
      role="status"
      aria-live="polite"
    >
      <div className="pipeline-header">
        <h2 className="pipeline-title">{messages.loaderTitle}</h2>
        <p className="pipeline-hint">{messages.loaderHint}</p>
      </div>

      <div className="pipeline-progress" aria-hidden="true">
        <span
          className="pipeline-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>

      <ol className="pipeline-steps">
        {pipelineStages.map((stage, index) => {
          const state =
            index < activeStep
              ? "done"
              : index === activeStep
                ? "active"
                : "pending";
          return (
            <li key={stage.key} className={`pipeline-step is-${state}`}>
              <span className="pipeline-step-icon" aria-hidden="true">
                {state === "done" ? <CheckIcon /> : null}
                {state === "active" ? (
                  <span className="pipeline-spinner" />
                ) : null}
              </span>
              <span className="pipeline-step-text">
                <span className="pipeline-step-label">{stage.label}</span>
                <span className="pipeline-step-sub">{stage.hint}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5 12.5 10 17.5 19 7"
      />
    </svg>
  );
}
