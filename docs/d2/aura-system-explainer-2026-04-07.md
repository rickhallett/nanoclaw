---
title: "Aura System Explainer — What We're Building and How It Thinks"
category: analysis
status: active
created: 2026-04-07
---

# Aura — What We're Building and How It Thinks

You asked a beautiful question: *how does this actually work?*

Most AI tools are a single brain doing everything — writing, judging, remembering. That's like asking the same student to take the exam and grade it. The result is predictable: flattery disguised as quality. The industry calls this **sycophancy** — the AI's tendency to agree with you, please you, and produce things that *sound* good but aren't necessarily *true* to your voice.

We're building something deliberately different. Here's how.

## 1. Your dictionary comes first, not the content

Before the system writes a single word for you, we're building a living glossary of your world — Microcosmic Orbit, Chi Nei Tsang, nudan, the 6 Healing Sounds, all of it. Every term spelled correctly, defined in context, with common mistranscriptions flagged.

Why: Without this, the AI hears you say "Microcosmic Orbit" and writes "Microsoft Orbit." Everything downstream is corrupted. The dictionary is the foundation. It feeds into both your transcription and your content quality checks.

## 2. Three separate intelligences, not one

Your system uses AI models in distinct roles that deliberately check each other:

### The Listener (Deepgram Nova-3)

A specialised speech-to-text model. Not creative, not clever. Its only job is turning your Zoom recordings into accurate text, with your dictionary correcting domain terms it would otherwise mangle. Think of it as a very attentive, very literal scribe.

### The Alchemist (Claude, generating)

This is your Content Alchemist. It reads your transcripts and creates Instagram posts in your voice. It has studied your intake conversation deeply — your rhythm, your softness, the way you explain "skin breathing through every pore." It generates. That's all it does.

### The Judge (Claude, evaluating — separate instance, separate instructions)

This is the quality gate. It receives the Alchemist's output and scores it against six criteria we derived from *your actual communication patterns*:

| Criterion | What it measures | Weight |
|-----------|-----------------|--------|
| **Tone** | Does this sound like you — soft, educational, meditative? Or generic Instagram wellness? | High |
| **Terminology** | Are the UHT terms correct and contextually appropriate? | High |
| **Safety** | Does this make health claims you'd never make? | Highest |
| **Lao Tzu** | If a quote appears, is it woven naturally — or bolted on? | Low |
| **Instagram readiness** | Right length, good rhythm, a hook that invites rather than demands? | Medium |
| **Lineage** | Is Master Chia's system referenced with integrity? | Medium |

The Judge doesn't know what the Alchemist was trying to do. It only knows what *your voice* sounds like, and whether the output matches. This separation is deliberate — it prevents the system from grading its own homework.

## 3. Hard rules that no AI can override

Some protections aren't AI at all. We have a deterministic deny-list — a set of word combinations that are *never* allowed through, regardless of what any model thinks. If the system produces a sentence combining words like "cure," "heal," or "fix" with any health condition, it's blocked automatically. No judgement call, no negotiation.

Your approved language — "return to," "cultivate," "invite," "create space for" — is explicitly encoded. The system knows the difference between "this practice may support your wellbeing" and "this will heal your anxiety." The first is you. The second is a liability.

## 4. You are always the final authority

Nothing publishes without your explicit approval. Every piece of content arrives in Telegram with its quality score visible. You see what the Judge thought. You approve, edit, or reject. Your decisions become the training data that makes the system better over time.

After you've approved or rejected 20+ pieces, the system starts learning your preferences — not what it *thinks* you want, but what you *actually* chose. This is the difference between a tool that flatters you and a tool that learns from you.

## 5. The system watches itself for drift

AI degrades over time. What sounds like you today can slowly drift toward generic wellness copy over weeks and months. We track quality scores across every piece generated. If the rolling average drops, we catch it before you notice. Prompt adjustments are versioned, tested against your baseline, and reversible.

## The honest summary

We're not building a magic box. We're building a system of checks and balances — multiple specialised models that don't trust each other, hard rules that override AI judgement on safety, and your voice as the ultimate authority. The goal is a tool that sounds like you on its best days, and catches itself on its worst.

The first thing we'll ship is the dictionary and the quality scoring — before any content. Because getting your voice right is more important than getting content fast.
