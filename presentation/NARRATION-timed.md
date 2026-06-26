# Narration — timed to the slides (for text-to-speech)

Total: ~3:00 at ~150 words/minute. Advance to the next slide at each timecode.
Each block is clean spoken text only — safe to paste straight into a TTS engine.

---

**SLIDE 1 · 0:00–0:09**
Hi, I'm Rosario Barbagallo, and this is AI Agile Delivery Governance: a governed, two-agent system built on Microsoft Foundry.

**SLIDE 2 · 0:09–0:27**
Every agile team shares the same quiet problem. User stories enter the backlog inconsistently. They're vague, they have no acceptance criteria, no clear value, or scope that's far too big. The cost shows up later, in wasted planning time, and sometimes in building the wrong thing.

**SLIDE 3 · 0:27–0:42**
So I built two agents with opposite jobs. The first one critiques. The second one creates. One evaluates a story; the other plans it. They never overlap, and that clean separation is what makes this a real, multi-agent system, not one prompt cut in two.

**SLIDE 4 · 0:42–1:04**
Here's the whole system. A story goes into the governance agent, which scores it against the INVEST criteria and the team's definition of ready. Then comes the key part: the quality gate. It branches. If the story passes, it flows to the planning agent and becomes ready-to-build work. If it fails, it's sent back with clear feedback, and it stops.

**SLIDE 5 · 1:04–1:19**
The governance agent calls a tool that runs the quality checks, then returns a structured verdict: a score, a pass or fail decision, and an explicit list of issues. That structured output is the linchpin of the whole design.

**SLIDE 6 · 1:19–1:33**
When a story passes, the planning agent takes it as approved. It doesn't re-judge quality. It produces the delivery plan: an estimate with rationale, a task breakdown, the definition of done, and the risks. Work the team can pick up right away.

**SLIDE 7 · 1:33–1:48**
Why does the gate matter so much? Because structured output does double duty. It makes the gate actionable, so the workflow can branch on a real decision. And it makes the agent measurable, so I can score its decisions against ground truth.

**SLIDE 8 · 1:48–2:01**
Everything runs on Microsoft Foundry, across five pillars. Two purpose-built agents. Tools and grounding. Full tracing. Quality evaluation. And a deployable workflow that you can invoke by name.

**SLIDE 9 · 2:01–2:18**
This is where governance becomes real. Every agent call is traced into Application Insights, so the gate pass rate becomes a measurable metric. And the governance agent is evaluated against a labelled set of stories with an automated judge. Monitoring tells me the system is running. Evaluation tells me it's right.

**SLIDE 10 · 2:18–2:33**
I measured it three ways. For correctness, against a labelled golden set, the gate's decisions match human judgement ninety-three percent of the time. For quality, Foundry's automated judge rates the output high on coherence and intent. And for safety, a clean sweep across every dimension.

**SLIDE 11 · 2:33–2:48**
So what does this give a team? Faster, more consistent sprint planning. A quality gate that's measurable instead of subjective. And, the part I care about most, a governance system that is itself governed. You trust the output because it's measured.

**SLIDE 12 · 2:48–2:53**
Governed delivery, from requirement to ready. Thank you.
