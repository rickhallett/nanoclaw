# Engineering Assessment: Aura Content Pipeline

**Source:** Gemini engineering analysis (2026-04-05)
**Scope:** Technical feasibility of Content Alchemist and Dao Assistant agents

---

## 1. The Transcription Trap (Whisper vs. The Dao)

An 80-minute Zoom call is about 10,000 to 12,000 words. Passing that through an LLM is cheap and easy now. The bottleneck is transcription accuracy.

- **Reality:** Standard Whisper models will hallucinate on "Microcosmic Orbit," "Sphincter of Oddi," and "beheading the red dragon."
- **Fix:** Custom prompt/dictionary to the speech-to-text engine (Whisper's `prompt` parameter) loaded with Universal Healing Tao jargon. Otherwise the LLM thinks she's talking about Game of Thrones.

## 2. The "Golden Moments" Clipping Problem (The Hardest Part)

She wants the Content Alchemist to automatically edit video and pull out "golden moments" for Instagram.

- **Reality:** LLMs cannot sense when the "qi is flowing" in a video. Automated video clipping via FFmpeg based purely on text transcripts often results in jarring, mid-breath cuts.
- **Fix:** Use an LLM to scan the transcript, identify 30-60 second semantic blocks with high "wisdom density," return start/stop timestamps. Pad timestamps by +2/-2 seconds and use FFmpeg to clip. 
- **Expectation management:** She must review these clips. The bot will find the right words, but it won't know if she was scratching her nose or out of frame when she said them.

## 3. The Copywriting & Voice (The Easiest Part)

- **Reality:** Usually, getting an AI to stop sounding like a LinkedIn hustle-bro is a nightmare.
- **Fix:** She practically wrote her own system prompt during the intake. Her exact rules: no hype, no sales, use line breaks, quote Lao Tzu, sound like a practitioner. Dump the clipped transcript into a prompt with these constraints — reliable output.

## 4. The "Dao Assistant" Course Structuring

- **Reality:** She wants to take 80 minutes of rambling and break it into four neat, 20-minute sellable course modules.
- **Fix:** Easy semantic chunking task. Full transcript → LLM clusters topics chronologically → markdown syllabus. Computationally cheap. Saves her hours of Sunday brain-drain.

## Proposed Tech Stack

```
Zoom API/Webhook → Whisper (w/ custom dictionary) → Long-context LLM (copy + timestamps) → FFmpeg (clipping) → Drafts folder
```

## Delivery Model

Do not offer final-render video editing. Offer an assembler. The Content Alchemist delivers a Sunday package:

1. Raw clipped MP4s (the "Golden Threads")
2. Ready-to-post Instagram captions
3. Parsed 4-part course syllabus

She explicitly said she wants to do "an extra click for refinement" because "the body leads, not the mind." Let her body do the final video transitions.

## Revenue Model

- Setup fee for custom prompt tuning (Whisper dictionary, voice calibration)
- Monthly compute retainer for pipeline execution
