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
  prompt: string;
  onGenerate: (request: NonNullable<PlannerClarificationResponse["trip_request"]>) => void;
  isLoading: boolean;
}

function dateLabel(value: string | null): string {
  return value ? new Date(`${value}T12:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "Not set";
}

export default function QuickPlanner({ prompt, onGenerate, isLoading }: QuickPlannerProps) {
  const [answers, setAnswers] = useState<PlannerAnswer[]>([]);
  const [response, setResponse] = useState<PlannerClarificationResponse | null>(null);
  const [customAnswer, setCustomAnswer] = useState("");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);

  const activeQuestion = useMemo(() => {
    if (!response) return null;
    return response.questions.find((question) => !answers.some((answer) => answer.question_id === question.id)) || null;
  }, [answers, response]);

  const askPlanner = async (nextAnswers: PlannerAnswer[]) => {
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

  // Auto-start the clarification flow on mount
  if (!started && prompt.trim().length >= 3) {
    setStarted(true);
    void askPlanner([]);
  }

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
  const preferences = brief?.preferences || { experiences: [], pace: null };

  if (!response && !isAsking && !error) {
    return (
      <div className="clarification-section" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>✍️</div>
        <p style={{ fontWeight: 600, color: "var(--foreground)" }}>Understanding your trip…</p>
        <p style={{ fontSize: "0.85rem", color: "var(--foreground-muted)", marginTop: "0.25rem" }}>Gemini is parsing your request</p>
      </div>
    );
  }

  return (
    <div className="clarification-section" aria-live="polite">
      {error && <p style={{ color: "var(--error)", fontSize: "0.85rem", marginBottom: "1rem", padding: "0.75rem", background: "rgba(239,68,68,0.06)", borderRadius: 8, border: "1px solid rgba(239,68,68,0.15)" }} role="alert">{error}</p>}

      {response && brief && (
        <>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--foreground-muted)" }}>Trip brief</span>
            <span style={{
              borderRadius: 20,
              padding: "0.25rem 0.6rem",
              fontSize: "0.7rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              background: response.status === "ready" ? "rgba(34,197,94,0.1)" : "rgba(232,144,31,0.1)",
              color: response.status === "ready" ? "var(--success)" : "var(--marigold)",
            }}>
              {response.status === "ready" ? "Generating" : "One more step"}
            </span>
          </div>

          <dl style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem 1.5rem", fontSize: "0.85rem" }}>
            <div><dt style={{ color: "var(--foreground-muted)", fontSize: "0.78rem" }}>Route</dt><dd style={{ fontWeight: 600, color: "var(--foreground)", marginTop: "0.15rem" }}>{brief.origin || "Not set"} → {brief.destination || "Not set"}</dd></div>
            <div><dt style={{ color: "var(--foreground-muted)", fontSize: "0.78rem" }}>Dates</dt><dd style={{ fontWeight: 600, color: "var(--foreground)", marginTop: "0.15rem" }}>{dateLabel(brief.start_date)} – {dateLabel(brief.end_date)}</dd></div>
            <div><dt style={{ color: "var(--foreground-muted)", fontSize: "0.78rem" }}>Members</dt><dd style={{ fontWeight: 600, color: "var(--foreground)", marginTop: "0.15rem" }}>{brief.members || "Not set"}</dd></div>
            <div><dt style={{ color: "var(--foreground-muted)", fontSize: "0.78rem" }}>Budget</dt><dd style={{ fontWeight: 600, color: "var(--foreground)", marginTop: "0.15rem" }}>{brief.budget ? `₹${brief.budget.toLocaleString("en-IN")}` : "Not set"}</dd></div>
          </dl>

          {(preferences.experiences.length > 0 || preferences.pace) && (
            <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }} aria-label="Trip preferences">
              {preferences.experiences.map((exp) => <span key={exp} style={{ padding: "0.2rem 0.5rem", borderRadius: 16, background: "rgba(28,128,121,0.08)", color: "var(--teal-india)", fontSize: "0.72rem", fontWeight: 600 }}>{exp}</span>)}
              {preferences.pace && <span style={{ padding: "0.2rem 0.5rem", borderRadius: 16, background: "rgba(232,144,31,0.08)", color: "var(--marigold)", fontSize: "0.72rem", fontWeight: 600, textTransform: "capitalize" }}>{preferences.pace} pace</span>}
            </div>
          )}

          {activeQuestion && (
            <div style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid var(--glass-border)" }}>
              <p style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--foreground)" }}>{activeQuestion.prompt}</p>

              {activeQuestion.input_type === "choice" && (
                <>
                  <div style={{ display: "grid", gap: "0.5rem", gridTemplateColumns: "1fr 1fr", marginTop: "0.75rem" }}>
                    {activeQuestion.options.map((option, index) => (
                      <button
                        key={option.id}
                        type="button"
                        disabled={isAsking}
                        onClick={() => submitAnswer(activeQuestion, option.label, option.id)}
                        style={{
                          padding: "0.65rem 0.75rem",
                          borderRadius: 8,
                          border: "1px solid var(--glass-border)",
                          background: "var(--background)",
                          textAlign: "left",
                          fontSize: "0.82rem",
                          color: "var(--foreground-secondary)",
                          cursor: "pointer",
                          transition: "border-color 0.18s, color 0.18s",
                        }}
                      >
                        <span style={{ color: "var(--marigold)", marginRight: "0.4rem" }}>{index + 1}.</span>
                        {option.label}
                      </button>
                    ))}
                  </div>
                  {activeQuestion.allow_custom && (
                    <form onSubmit={submitCustomAnswer} style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
                      <input
                        required
                        value={customAnswer}
                        onChange={(e) => setCustomAnswer(e.target.value)}
                        placeholder="Type something else…"
                        style={{ flex: 1, padding: "0.55rem 0.75rem", borderRadius: 8, border: "1px solid var(--glass-border)", background: "var(--background)", fontSize: "0.82rem", color: "var(--foreground)", outline: "none" }}
                      />
                      <button
                        type="submit"
                        disabled={isAsking}
                        style={{ padding: "0.55rem 0.75rem", borderRadius: 8, border: "1px solid rgba(232,144,31,0.4)", background: "transparent", color: "var(--marigold)", fontSize: "0.82rem", fontWeight: 700, cursor: "pointer" }}
                      >
                        Use
                      </button>
                    </form>
                  )}
                </>
              )}

              {activeQuestion.input_type !== "choice" && (
                <form onSubmit={submitCustomAnswer} style={{ marginTop: "0.75rem" }}>
                  {activeQuestion.input_type === "date_range" ? (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                      <input required type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} style={{ padding: "0.55rem", borderRadius: 8, border: "1px solid var(--glass-border)", background: "var(--background)", fontSize: "0.82rem", color: "var(--foreground)" }} />
                      <input required type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} style={{ padding: "0.55rem", borderRadius: 8, border: "1px solid var(--glass-border)", background: "var(--background)", fontSize: "0.82rem", color: "var(--foreground)" }} />
                    </div>
                  ) : (
                    <input
                      required
                      type={activeQuestion.input_type === "number" ? "number" : "text"}
                      value={customAnswer}
                      onChange={(e) => setCustomAnswer(e.target.value)}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 8, border: "1px solid var(--glass-border)", background: "var(--background)", fontSize: "0.82rem", color: "var(--foreground)", outline: "none" }}
                    />
                  )}
                  <button
                    type="submit"
                    disabled={isAsking}
                    className="hero-search-button"
                    style={{ marginTop: "0.75rem", padding: "0.6rem 1.2rem", fontSize: "0.85rem" }}
                  >
                    Continue
                  </button>
                </form>
              )}
            </div>
          )}

          {!activeQuestion && response.status === "questions" && (
            <p style={{ marginTop: "1rem", fontSize: "0.82rem", color: "var(--warning)" }}>
              I need one more detail. Try answering the question again or restart with a more detailed prompt.
            </p>
          )}
        </>
      )}
    </div>
  );
}
