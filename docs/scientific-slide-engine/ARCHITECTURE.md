# Scientific Slide Engine M0

## Purpose

The Scientific Slide Engine treats approved academic slide masters as source code. Its first invariant is content fidelity: scientific copy and speaker notes are locked unless a later, explicit editing mode is selected.

## Pipeline

```text
MASTER.md
  -> deterministic parser
  -> ScientificSlideSpec[]
  -> strict content locks
  -> layout/archetype planning
  -> editable presentation export
  -> structural/content/PPTX QA
```

This deliberately bypasses curriculum generation for complete masters. Presenton's normal outline and story generation remain useful for ordinary prompts, but strict materialization must not ask an LLM to rewrite already-approved scientific content.

## Modes

### STRICT_MATERIALIZE

Allowed: layout selection, geometry, line breaks, visual emphasis, diagram routing and asset strategy.

Not allowed: rewriting approved copy, adding claims, removing claims, changing notes, merging, splitting or reordering slides.

### VISUAL_ENHANCE

Reserved for later work. It keeps the same scientific locks while allowing richer visual execution.

## Public/private separation

The public fork contains only generic parser, schema, lock and QA code plus synthetic tests. Private course masters and benchmark decks must stay in an authenticated private checkout or in the private content repository.

## Current M0 baseline

- Upstream baseline: `presenton/presenton@4b4e88e705180dabffb4e2d9aae71cede22fbb0e`.
- Standard generation is the preferred foundation for strict materialization because it keeps fixed layouts and template compatibility.
- Smart generation is useful later for adaptive composition, but its default path is content-generation oriented.
- `PRESENTON_MAX_SLIDES` now controls the backend slide ceiling; frontend generation controls can be aligned via `NEXT_PUBLIC_PRESENTON_MAX_SLIDES`/`PRESENTON_MAX_SLIDES`.

## M0 limitations

- Speaker-note preservation still needs integration into Presenton's persisted/export data model. The private benchmark harness verifies notes through direct PPTX generation, while the public Presenton path needs a native note field.
- The frontend slide limit should ultimately read a backend capabilities endpoint to eliminate any environment-variable drift.
- The first public tests use synthetic fixtures only; private 600-slide validation is executed in the private content repository.
