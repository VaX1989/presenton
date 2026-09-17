# Scientific Slide Engine M0

## Purpose

The Scientific Slide Engine treats an approved academic master as source code. `ScientificSlideSpec` is the intermediate representation, `VisualPlan` is layout IR, Presenton is the compiler/runtime, and PPTX/PDF are production artifacts.

The non-negotiable invariant is scientific fidelity: strict mode may change geometry, grouping and visual hierarchy, but it may not author scientific prose.

## Native pipeline

```text
RICH_A_S_MASTER (preferred) / COMPACT_FINAL_LEGACY
  -> deterministic parser
  -> ScientificSlideSpec[]
  -> immutable locked content
  -> deterministic archetype + authored visual-slot planning
  -> editable Template V2 text/vector UI
  -> normal PresentationModel + SlideModel persistence
  -> exact SlideModel.speaker_note
  -> existing Presenton editor/export pathway
  -> PPTX / PDF
  -> content, notes, structural and render QA
```

`POST /api/v1/ppt/scientific/generate` implements this path. It does not call outline generation, story generation, copy generation, slide splitting/merging or automatic reordering.

## Immutable and mutable layers

Immutable in `strict_materialize`:

- slide identity and order;
- title/subtitle/visible text/callouts/caption/question;
- final speaker notes;
- authored visual labels and scientific data;
- source hash.

Mutable presentation concerns:

- archetype selection among compatible layouts;
- geometry within authored constraints;
- line routing and grouping;
- light/dark variant where permitted;
- native vector implementation;
- asset placement when an authored asset strategy permits it.

Every visible text element emitted by the strict renderer is checked against the canonical slide source block. Unsourced renderer prose is a hard failure.

## Rich source support

The preferred parser consumes the full A–S master DSL and preserves each section in `raw_sections`. Unknown canonical material must never disappear silently. Compact `G###` masters remain supported as a compatibility format only.

See `MASTER_FORMAT.md`.

## Native Presenton integration

Strict output is persisted using normal Presenton models:

- `PresentationModel.version = V2_STANDARD`;
- `SlideModel.ui` contains editable Template V2 text/vector primitives;
- `SlideModel.speaker_note` contains the exact final note;
- slide scientific metadata stores source hash, global/local IDs, archetype, theme and render contract.

Persistence is transactional: exact locked fields are checked after `flush()` and before commit, then checked again after commit/readback.

## Rendering

The `scientific-editorial` theme and archetype registry are public and generic. The renderer consumes authored coordinates when available, `EXACT_LABELS` for diagrams, canonical matrix cells and chart annotations. It does not flatten a slide to a background image.

## Capabilities

`GET /api/v1/ppt/scientific/capabilities` is authoritative for `max_slides`, strict-mode support, notes support, master formats, theme and archetypes. The Next.js UI proxies and consumes this endpoint rather than maintaining an independent slide ceiling.

The default backend maximum is 100 and can be changed with `PRESENTON_MAX_SLIDES`.

## Security boundary

The public fork contains generic engine code, generic academic design tokens, synthetic tests and documentation only. Course masters, course speaker notes, generated course decks and rendered screenshots stay in the private content repository/runtime.

## Baseline

The M0 fork was based on `presenton/presenton@4b4e88e705180dabffb4e2d9aae71cede22fbb0e`. Upstream synchronization is documented separately and must not overwrite strict scientific invariants.
