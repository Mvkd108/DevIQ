# Data Provenance Guide

Use this before any evaluator walkthrough, pilot, or customer-facing demo.

## Why this matters

The product intentionally mixes different evidence strengths:

- directly stored records
- connector-backed stage data
- deterministic inferences
- placeholder coverage for showcase continuity

A truthful demo should explain which kind of evidence is being shown.

## Evidence tiers

### Real records

These are the strongest operational signals in the current product:

- requirement records stored in `req_code_mapping`
- commit or extension event records stored in `extension_events`
- persisted feedback and intake records when storage mode is Supabase-backed

Use these as the baseline for statements like:

- "this requirement exists"
- "this commit was captured"
- "this intake record was persisted"

### Connector-backed delivery stages

These are stronger than inferred stages because they come from explicit connector/event fields.

Examples:

- PR state from connector fields
- CI state from explicit run fields
- deployment state from explicit deployment fields

In the timeline UI these are labeled as connector-backed.

### Inferred stages

These are deterministic interpretations, not raw source-of-truth records.

Examples:

- PR inferred from linked branch or downstream signals
- CI inferred from linked activity
- deployment inferred from later-stage evidence
- summary judgments derived from workload, freshness, continuity risk, or delivery readiness

These are useful, but should be described as inferred rather than observed.

### Mocked stages

These are placeholders used when no delivery signal exists.

Purpose:

- preserve walkthrough continuity
- keep the UI structurally complete

Risk:

- they can be mistaken for real delivery evidence if not called out clearly

Never describe mocked stages as actual PR, CI, or deployment proof.

## How to read the timeline truthfully

When reviewing the delivery timeline:

- connector-backed stages are the strongest delivery-stage evidence
- inferred stages are weaker than connector-backed stages but still meaningful
- mocked stages are placeholders only

Practical rule:

- if a requirement shows mocked stages, call it out as incomplete delivery evidence

## How to read summaries truthfully

Summary sections can combine:

- observed facts
- inferred judgments

Treat them differently:

- observed facts are closer to source records
- inferred judgments are deterministic interpretations and should be presented as such

## What to check before a pilot

Use these checks before presenting the product:

- timeline provenance labels are visible
- the operator knows which sections are real, inferred, or mocked
- `/api/health` storage modes are understood
- snapshot-backed content is not mistaken for fresher-than-it-is data

## Safe language for demos

Prefer:

- "connector-backed"
- "inferred from linked activity"
- "placeholder coverage"
- "snapshot-backed"

Avoid:

- "fully real"
- "definitive deployment proof" when the stage is inferred or mocked
- "persisted" when storage mode is derived or fallback-only
