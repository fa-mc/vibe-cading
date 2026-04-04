---
agent: agent
description: "Lookback — Developer reflects on completed task, produces structured feedback"
---
# Phase: Lookback

This prompt is used by the **Developer** at the end of a task to produce a
structured lookback report.

## Instructions

1. Read the plan file from `.agents/plans/` for the current task.
2. Review everything that happened during execution: code written, tools
   run, escalations raised, validation results.
3. Create a lookback report in `.agents/lookback/` following the template at
   `docs/templates/lookback-template.md`.  Name it
   `YYYY-MM-DD-[task-slug].md`.

## Reflection prompts

Work through these questions to generate the feedback:

### Instruction gaps
- Was there a situation where `copilot-instructions.md` didn't provide
  guidance and you had to guess or ask?
- Did you make an assumption that turned out wrong because there was no
  rule covering it?
- Did you repeat a mistake that a rule could have prevented?

### Missing tools
- Did you manually do something that a script could automate?
- Did you run a long sequence of commands that could be a single tool?
- Did you wish you could query the geometry in a way no existing tool
  supports?
- Did you create a throwaway script in `tmp/` during this task that proved continuously useful and should be promoted to a permanent tool in `tools/` with a proper CLI layout?

### Plan deficiencies
- Were any deliverables underspecified?
- Did you have to make a design decision that the Designer should have made?
- Were dependencies between deliverables missing or wrong?
- Were validation commands incomplete or incorrect?

### Tooling bugs
- Did any tool in `tools/` produce unexpected output?
- Did any tool crash or hang?
- Did you have to work around a tool limitation?

## Output

Write the report to `.agents/lookback/YYYY-MM-DD-[task-slug].md` and summarise
the key findings to the user. Then, automatically transition to the `#admin` role for review without asking the user to manually invoke it.
