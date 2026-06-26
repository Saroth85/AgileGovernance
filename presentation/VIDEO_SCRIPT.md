# Video presentation script

**AI Agile Delivery Governance — a governed two-agent system on Microsoft Foundry**

Target length: ~3.5–4 minutes. Read at a calm pace. Slide cues in **[brackets]**.
The matching deck is `presentation/AI-Agile-Delivery-Governance-Slides.pptx`.

---

**[SLIDE 1 — Title]**

Hi. I'm Rosario Barbagallo, a software architect, and this is *AI Agile Delivery
Governance* — a governed, two-agent system built on Microsoft Foundry that takes a raw
user story and turns it into either ready-to-build work or precise feedback for the team.

**[SLIDE 2 — The problem]**

Every Agile team has the same quiet problem. User stories enter the backlog inconsistently
— vague wording, no acceptance criteria, no clear value, scope that's far too big. The cost
shows up later: sprint planning time is wasted refining stories that should never have
reached the board, and sometimes the team builds the wrong thing entirely. And the worst
part is that "is this story good enough?" is usually answered subjectively, differently by
every reviewer.

**[SLIDE 3 — The idea]**

So I built two agents with opposite jobs. The first one *critiques*. The second one
*creates*. The Backlog Governance Agent evaluates a story; the Sprint Planning Agent plans
it. They never overlap — and that clean separation is what makes this a real multi-agent
system, not one prompt cut in two.

**[SLIDE 4 — Architecture: the gate that branches]**

Here's the whole system. A story goes into the Governance Agent, which scores it against
INVEST and the team's Definition of Ready and returns a structured verdict. Then comes the
key part — the quality gate. It *branches*. If the story passes, it flows to the Planning
Agent and becomes ready-to-build work. If it fails, it's sent back with explicit,
actionable feedback, and it stops. That branch is the difference between a governed
workflow and a dumb pipe — bad stories never reach planning.

**[SLIDE 5 — Agent 1: Backlog Governance]**

The Governance Agent calls a tool that runs deterministic INVEST and Definition-of-Ready
checks, then reasons over the result and returns a JSON verdict: a score, a pass-or-fail
gate decision, and an explicit list of issues. That structured output is the linchpin of
the whole design.

**[SLIDE 6 — Agent 2: Sprint Planning]**

When a story passes, the Planning Agent takes it as approved — it doesn't re-judge quality
— and produces the delivery plan: a story-point estimate with rationale, a task breakdown,
the Definition of Done, and the risks. Work the team can pick up immediately.

**[SLIDE 7 — Why the gate matters]**

Why does the gate matter so much? Because structured output does double duty. It makes the
gate *actionable* — the workflow can branch on a real boolean. And it makes the agent
*measurable* — I can score its decisions against ground truth. Without it, you'd have
neither a reliable gate nor a real evaluation.

**[SLIDE 8 — Built on Microsoft Foundry]**

Everything runs on Microsoft Foundry, across the five pillars of the hackathon. Both agents
are created in the Foundry Agent Service and run through the Responses API. They're grounded
with tools and domain rules. They're traced. They're evaluated. And they're orchestrated
into a deployable workflow.

**[SLIDE 9 — Trust: observability and evaluation]**

This is where governance becomes real. Every agent call is traced into Application Insights
— and because the verdict is structured, the gate pass-rate and score distribution become
queryable metrics. Then evaluation: I run the Governance Agent against a labelled golden
set with LLM-as-judge scoring. Monitoring tells me the system is running; evaluation tells
me it's *right*.

**[SLIDE 10 — Results]**

On the golden set, the agent catches the seeded problems with high precision and recall,
and its gate decisions match the human labels the large majority of the time — and where
they don't, the evaluation surfaces exactly which cases to fix. That's the point: it's not
a demo that looks good, it's a system I can measure and improve.

**[SLIDE 11 — Why it matters]**

So what does this give a team? Faster, more consistent sprint planning. A quality gate
that's measurable instead of subjective. And — the part I care about most — a governance
system that is *itself* governed: every decision is traced, every agent is evaluated. You
don't trust the output because it sounds confident; you trust it because it's measured.

**[SLIDE 12 — Closing]**

Governed delivery, from requirement to ready. Thank you.

---

### Delivery notes
- Pause for a beat after "It *branches*" on slide 4 — it's the core idea.
- Slides 5–7 are the technical heart; keep the energy up but don't rush the gate.
- If you have extra time, on slide 9 mention that the tracing env vars must be set before
  the SDK import — a nice detail that shows you actually built it.
- End cleanly on slide 12; resist adding more.
