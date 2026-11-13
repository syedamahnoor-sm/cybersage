"use client";
import { useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  CircleHelp,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { assessRisk, ratings } from "@/lib/risk";
import { PageIntro } from "./page-intro";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
const likelihoodLabels = [
  "Rare",
  "Unlikely",
  "Possible",
  "Likely",
  "Almost certain",
];
const impactLabels = ["Negligible", "Minor", "Moderate", "Major", "Severe"];
export function RiskWorkspace() {
  const [likelihood, setLikelihood] = useState(3);
  const [impact, setImpact] = useState(4);
  const result = assessRisk(likelihood, impact);
  return (
    <>
      <PageIntro
        eyebrow="ASSESSMENT / DETERMINISTIC BY DESIGN"
        title="Put risk into perspective."
        description="Explore a scenario. Adjust the inputs. See exactly how the score is calculated."
        action={<Badge>Local calculation · No LLM</Badge>}
      />
      <div className="risk-layout">
        <section className="card risk-inputs">
          <div className="panel-heading">
            <span className="number-tag">01</span>
            <h2>Define your scenario</h2>
          </div>
          <p className="muted">
            Select the likelihood and potential impact of an event.
          </p>
          {[
            {
              name: "Likelihood",
              value: likelihood,
              set: setLikelihood,
              labels: likelihoodLabels,
              description: "How likely is this event to occur?",
            },
            {
              name: "Impact",
              value: impact,
              set: setImpact,
              labels: impactLabels,
              description: "How significant would the consequences be?",
            },
          ].map((input) => (
            <fieldset className="rating-field" key={input.name}>
              <legend>
                {input.name}
                <span>{input.labels[input.value - 1]}</span>
              </legend>
              <p>{input.description}</p>
              <div className="rating-group">
                {ratings.map((value) => (
                  <button
                    key={value}
                    type="button"
                    aria-label={`${input.name} ${value}: ${input.labels[value - 1]}`}
                    aria-pressed={input.value === value}
                    onClick={() => input.set(value)}
                    className={input.value === value ? "selected" : ""}
                  >
                    {value}
                  </button>
                ))}
              </div>
              <div className="rating-ends">
                <span>{input.labels[0]}</span>
                <span>{input.labels[4]}</span>
              </div>
            </fieldset>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setLikelihood(3);
              setImpact(4);
            }}
          >
            <RotateCcw size={14} />
            Reset inputs
          </Button>
          <div className="formula-note">
            <span>THE FORMULA</span>
            <p>
              Likelihood <b>×</b> Impact <b>=</b> Risk score
            </p>
          </div>
        </section>
        <section className="card matrix-panel">
          <div className="panel-heading">
            <span className="number-tag">02</span>
            <h2>Explore the risk matrix</h2>
          </div>
          <p className="muted">
            Select any cell to assess a different scenario.
          </p>
          <div className="matrix-wrap">
            <div className="matrix-y-label">
              LIKELIHOOD <ArrowDown size={12} />
            </div>
            <div className="matrix-content">
              {[5, 4, 3, 2, 1].map((l) => (
                <div className="matrix-row" key={l}>
                  <span className="matrix-axis-value">{l}</span>
                  {ratings.map((i) => {
                    const r = assessRisk(l, i);
                    return (
                      <button
                        type="button"
                        key={i}
                        className={`matrix-cell severity-${r.category.toLowerCase()} ${l === likelihood && i === impact ? "chosen" : ""}`}
                        aria-label={`Likelihood ${l}, impact ${i}: ${r.score}, ${r.category}`}
                        aria-pressed={l === likelihood && i === impact}
                        onClick={() => {
                          setLikelihood(l);
                          setImpact(i);
                        }}
                      >
                        {r.score}
                        {l === likelihood && i === impact && (
                          <span className="sr-only"> selected</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              ))}
              <div className="matrix-row matrix-bottom">
                <span />
                {ratings.map((i) => (
                  <span key={i}>{i}</span>
                ))}
              </div>
              <div className="matrix-x-label">
                IMPACT <ArrowRight size={12} />
              </div>
            </div>
          </div>
          <div className="matrix-legend">
            {["Low", "Medium", "High", "Critical"].map((c, index) => (
              <span key={c}>
                <i className={`legend-dot severity-${c.toLowerCase()}`} />
                {c}
                <small>{["1–5", "6–10", "11–15", "16–25"][index]}</small>
              </span>
            ))}
          </div>
        </section>
      </div>
      <section
        className={`risk-result severity-border-${result.category.toLowerCase()}`}
        aria-live="polite"
        aria-atomic="true"
      >
        <div className="risk-score">
          <span className="tiny-label">YOUR RISK SCORE</span>
          <p>
            <strong>{result.score}</strong>
            <span>/ 25</span>
          </p>
          <Badge className={`severity-${result.category.toLowerCase()}`}>
            {result.category} risk
          </Badge>
        </div>
        <div className="risk-interpretation">
          <h2>A transparent assessment.</h2>
          <p>{result.interpretation}</p>
          <div className="result-equation">
            <span>
              {likelihood}
              <small>Likelihood</small>
            </span>
            <b>×</b>
            <span>
              {impact}
              <small>Impact</small>
            </span>
            <b>=</b>
            <span>
              {result.score}
              <small>Risk score</small>
            </span>
          </div>
        </div>
        <div className="risk-limits">
          <CircleHelp size={20} />
          <h3>A decision aid, not a prediction.</h3>
          <p>{result.disclaimer}</p>
          <span>
            <ShieldCheck size={13} />
            Same formula as the backend risk tool
          </span>
        </div>
      </section>
    </>
  );
}
