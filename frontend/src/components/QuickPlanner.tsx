"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  api,
  ApiError,
  ClarificationQuestion,
  PlannerAnswer,
  PlannerClarificationResponse,
} from "@/lib/api";

interface QuickPlannerProps {
  onGenerate: (request: NonNullable<PlannerClarificationResponse["trip_request"]>) => void;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  "Plan five days from Delhi to Manali for two people under ₹30,000.",
  "Create a relaxed Goa trip for a couple in November with a ₹40,000 budget.",
  "Plan a three-day heritage trip from Mumbai to Jaipur for four members.",
  "Suggest a weekend road trip from Bengaluru to Coorg for three people.",
];

function dateLabel(value: string | null): string {
  return value ? new Date(`${value}T12:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "Not set";
}

export default function QuickPlanner({ onGenerate, isLoading }: QuickPlannerProps) {
  const [prompt, setPrompt] = useState("");
  const [answers, setAnswers] = useState<PlannerAnswer[]>([]);
  const [response, setResponse] = useState<PlannerClarificationResponse | null>(null);
  const [customAnswer, setCustomAnswer] = useState("");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeQuestion = useMemo(() => {
    if (!response) return null;
    return response.questions.find((question) => !answers.some((answer) => answer.question_id === question.id)) || null;
  }, [answers, response]);

  const askPlanner = async (nextAnswers: PlannerAnswer[], event?: FormEvent) => {
    event?.preventDefault();
    if (prompt.trim().length < 3 || isAsking) return;
    setIsAsking(true);
    setError(null);
    try {
      const next = await api.clarifyPlanner({ prompt: prompt.trim(), answers: nextAnswers });
      setAnswers(nextAnswers);
      setResponse(next);
      setCustomAnswer("");
      setCustomStart("");
      setCustomEnd("");
      if (next.status === "ready" && next.trip_request) onGenerate(next.trip_request);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "I could not understand that trip yet. Please try again.");
    } finally {
      setIsAsking(false);
    }
  };

  const submitPrompt = (event: FormEvent) => {
    setAnswers([]);
    setResponse(null);
    void askPlanner([], event);
  };

  const submitAnswer = (question: ClarificationQuestion, answer: string, optionId?: string) => {
    if (!answer.trim()) return;
    const nextAnswers = [
      ...answers.filter((item) => item.question_id !== question.id),
      { question_id: question.id, option_id: optionId || null, answer: answer.trim() },
    ];
    void askPlanner(nextAnswers);
  };

  const submitCustomAnswer = (event: FormEvent) => {
    event.preventDefault();
    if (!activeQuestion) return;
    const value = activeQuestion.input_type === "date_range"
      ? `${customStart} to ${customEnd}`
      : customAnswer;
    submitAnswer(activeQuestion, value);
  };

  const brief = response?.brief;

  return (
    <section className="mx-auto mb-8 max-w-[1180px] rounded-[10px] border border-marigold/30 bg-[linear-gradient(120deg,rgba(196,82,43,0.18),rgba(28,128,121,0.12))] p-5 shadow-[0_24px_60px_-36px_rgba(242,169,59,0.55)] sm:p-7" aria-labelledby="quick-plan-heading">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.72fr)] lg:items-start">
        <div>
          <div className="flex items-center gap-2 font-[family-name:var(--font-space-mono)] text-[11px] uppercase tracking-[0.16em] text-marigold">
            <span className="h-2 w-2 rounded-full bg-marigold" aria-hidden="true" /> Quick planning
          </div>
          <h2 id="quick-plan-heading" className="mt-2 font-[family-name:var(--font-teko)] text-[clamp(2rem,4vw,3rem)] font-semibold uppercase leading-none text-foreground">
            Tell us once. We&apos;ll ask what&apos;s missing.
          </h2>
          <p className="mt-2 max-w-[58ch] text-sm font-medium text-foreground-secondary">
            Describe the trip naturally. Gemini turns it into a plan request and asks only the few details needed before generating your itinerary.
          </p>
          <form onSubmit={submitPrompt} className="mt-5 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="quick-plan-prompt" className="sr-only">Describe your trip</label>
            <input
              id="quick-plan-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="e.g. Plan five days from Delhi to Goa under ₹30,000"
              className="min-w-0 flex-1 rounded-[3px] border border-glass-border bg-black/25 px-4 py-3 text-sm font-medium text-foreground outline-none transition-colors placeholder:text-foreground-muted focus:border-marigold focus:ring-1 focus:ring-marigold/40"
              maxLength={2000}
            />
            <button type="submit" disabled={prompt.trim().length < 3 || isAsking || isLoading} className="rounded-[3px] bg-marigold px-5 py-3 font-[family-name:var(--font-space-mono)] text-xs font-bold uppercase tracking-wide text-[#24160a] transition hover:shadow-[0_6px_24px_rgba(242,169,59,0.3)] disabled:cursor-not-allowed disabled:opacity-50">
              {isAsking ? "Thinking…" : "Plan this trip"}
            </button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2" aria-label="Suggested prompts">
            {EXAMPLE_PROMPTS.map((example) => (
              <button key={example} type="button" onClick={() => setPrompt(example)} className="rounded-full border border-glass-border bg-black/10 px-3 py-1.5 text-left text-[11px] text-foreground-secondary transition hover:border-marigold hover:text-foreground">
                {example}
              </button>
            ))}
          </div>
          {error && <p className="mt-4 rounded border border-error/30 bg-error/10 p-3 text-xs text-error" role="alert">{error}</p>}
        </div>

        <div className="min-h-[210px] rounded-[6px] border border-glass-border bg-background/45 p-4" aria-live="polite">
          {!response && (
            <div className="flex h-full flex-col justify-center">
              <span className="text-2xl" aria-hidden="true">✍️</span>
              <p className="mt-2 text-sm font-semibold text-foreground">Your trip conversation will appear here.</p>
              <p className="mt-1 text-xs text-foreground-muted">The planner will turn your sentence into an itinerary.</p>
            </div>
          )}
          {response && brief && (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-foreground-muted">Trip brief</span>
                <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${response.status === "ready" ? "bg-success/15 text-success" : "bg-warning/15 text-warning"}`}>
                  {response.status === "ready" ? "Generating" : "One more step"}
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                <div><dt className="text-foreground-muted">Route</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.origin || "Not set"} → {brief.destination || "Not set"}</dd></div>
                <div><dt className="text-foreground-muted">Dates</dt><dd className="mt-0.5 font-semibold text-foreground">{dateLabel(brief.start_date)} – {dateLabel(brief.end_date)}</dd></div>
                <div><dt className="text-foreground-muted">Members</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.members || "Not set"}</dd></div>
                <div><dt className="text-foreground-muted">Budget</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.budget ? `₹${brief.budget.toLocaleString("en-IN")}` : "Not set"}</dd></div>
              </dl>
              {(brief.preferences.experiences.length > 0 || brief.preferences.pace) && (
                <div className="mt-4 flex flex-wrap gap-1.5" aria-label="Trip preferences">
                  {brief.preferences.experiences.map((experience) => <span key={experience} className="rounded-full bg-teal-india/15 px-2 py-1 text-[10px] font-semibold text-teal-india">{experience}</span>)}
                  {brief.preferences.pace && <span className="rounded-full bg-marigold/15 px-2 py-1 text-[10px] font-semibold capitalize text-marigold">{brief.preferences.pace} pace</span>}
                </div>
              )}
              {activeQuestion && (
                <div className="mt-5 border-t border-glass-border pt-4">
                  <p className="text-sm font-semibold text-foreground">{activeQuestion.prompt}</p>
                  {activeQuestion.input_type === "choice" && (
                    <>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {activeQuestion.options.map((option, index) => (
                          <button key={option.id} type="button" disabled={isAsking} onClick={() => submitAnswer(activeQuestion, option.label, option.id)} className="rounded border border-glass-border bg-black/10 px-3 py-2 text-left text-xs text-foreground-secondary transition hover:border-marigold hover:text-foreground disabled:opacity-50">
                            <span className="mr-2 text-marigold">{index + 1}.</span>{option.label}
                          </button>
                        ))}
                      </div>
                      {activeQuestion.allow_custom && (
                        <form onSubmit={submitCustomAnswer} className="mt-3 flex gap-2">
                          <input required value={customAnswer} onChange={(event) => setCustomAnswer(event.target.value)} placeholder="Type something else…" className="min-w-0 flex-1 rounded border border-glass-border bg-black/20 px-3 py-2 text-xs text-foreground" />
                          <button type="submit" disabled={isAsking} className="rounded border border-marigold/60 px-3 py-2 text-xs font-bold text-marigold disabled:opacity-50">Use</button>
                        </form>
                      )}
                    </>
                  )}
                  {activeQuestion.input_type !== "choice" && (
                    <form onSubmit={submitCustomAnswer} className="mt-3 space-y-2">
                      {activeQuestion.input_type === "date_range" ? (
                        <div className="grid grid-cols-2 gap-2">
                          <input required type="date" value={customStart} onChange={(event) => setCustomStart(event.target.value)} className="rounded border border-glass-border bg-black/20 px-2 py-2 text-xs text-foreground" />
                          <input required type="date" value={customEnd} onChange={(event) => setCustomEnd(event.target.value)} className="rounded border border-glass-border bg-black/20 px-2 py-2 text-xs text-foreground" />
                        </div>
                      ) : (
                        <input required type={activeQuestion.input_type === "number" ? "number" : "text"} value={customAnswer} onChange={(event) => setCustomAnswer(event.target.value)} className="w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-xs text-foreground" />
                      )}
                      <button type="submit" disabled={isAsking} className="rounded bg-marigold px-3 py-2 text-xs font-bold text-[#24160a] disabled:opacity-50">Continue</button>
                    </form>
                  )}
                </div>
              )}
              {!activeQuestion && response.status === "questions" && <p className="mt-4 text-xs text-warning">I need one more detail. Try answering the question again or add it to your prompt.</p>}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
