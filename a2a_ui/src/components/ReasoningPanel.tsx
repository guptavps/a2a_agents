import { useId, useState } from 'react'
import type { StepItem } from '../state/types.ts'

interface ReasoningPanelProps {
  steps: StepItem[]
  running: boolean
}

function Step({ step }: { step: StepItem }) {
  if (step.kind === 'intent') {
    return (
      <li className="step step--intent">
        <span className="step__label">
          Intent: {step.intent.replace(/_/g, ' ')} ({Math.round(step.confidence * 100)}%)
        </span>
        <span className="step__text">{step.rationale}</span>
      </li>
    )
  }
  return <li className={`step step--${step.kind}`}>{step.text}</li>
}

// Open while the agent works; callers re-key this on completion so it collapses by default.
export function ReasoningPanel({ steps, running }: ReasoningPanelProps) {
  const [override, setOverride] = useState<boolean | undefined>(undefined)
  const bodyId = useId()
  const open = override ?? running
  const title = running ? 'Working\u2026' : `Reasoning \u00b7 ${steps.length} ${steps.length === 1 ? 'step' : 'steps'}`

  return (
    <section className="reasoning" aria-label="Agent reasoning">
      <button
        type="button"
        className="reasoning__toggle"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOverride(!open)}
      >
        <span className={`reasoning__chevron${open ? ' reasoning__chevron--open' : ''}`} aria-hidden="true">
          &#9656;
        </span>
        <span>{title}</span>
        {running && <span className="spinner" aria-hidden="true" />}
      </button>
      <div id={bodyId} className="reasoning__body" hidden={!open}>
        {steps.length === 0 ? (
          <p className="reasoning__empty">Waiting for the agent&hellip;</p>
        ) : (
          <ol className="steps">
            {steps.map((step, index) => (
              <Step key={index} step={step} />
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}
